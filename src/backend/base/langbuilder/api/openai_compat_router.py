from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Security
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import select

from langbuilder.api.v1.endpoints import simple_run_flow
from langbuilder.api.v1.schemas import SimplifiedAPIRequest
from langbuilder.helpers.flow import get_flow_by_id_or_endpoint_name
from langbuilder.services.auth.utils import api_key_header, api_key_query, api_key_security
from langbuilder.services.database.models.flow.model import AccessTypeEnum, Flow, FlowRead
from langbuilder.services.deps import session_scope

if TYPE_CHECKING:
    from langbuilder.services.database.models.user.model import UserRead
else:  # pragma: no cover - runtime fallback for forward annotations
    UserRead = Any  # type: ignore[assignment]

router = APIRouter(tags=["OpenAI-Compatible"])


# --- minimal OpenAI request/response types ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = 0.2
    stream: bool | None = False
    max_tokens: int | None = None


def _extract_text(payload: Any) -> str:
    """Extract a human-readable response from LangBuilder run payloads."""
    if isinstance(payload, str):
        return payload

    def ensure_text(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        return None

    def best_from_message(msg: Any) -> str | None:
        if isinstance(msg, dict):
            # order matters: message -> text -> data.text
            candidates = [
                msg.get("message"),
                msg.get("text"),
                msg.get("data", {}).get("text") if isinstance(msg.get("data"), dict) else None,
            ]
            for candidate in candidates:
                text = ensure_text(candidate)
                if text:
                    return text
        elif isinstance(msg, list):
            for item in msg:
                text = best_from_message(item)
                if text:
                    return text
        return ensure_text(msg)

    if isinstance(payload, dict):
        outputs = payload.get("outputs") or []
        for run_output in outputs:
            if not isinstance(run_output, dict):
                continue
            # check nested result entries
            for result_entry in run_output.get("outputs") or []:
                if not isinstance(result_entry, dict):
                    continue
                text = (
                    best_from_message(result_entry.get("results"))
                    or best_from_message(result_entry.get("outputs"))
                    or best_from_message(result_entry.get("messages"))
                )
                if text:
                    return text
        # fallback to recursive search
        for value in payload.values():
            text = best_from_message(value)
            if text:
                return text

    if isinstance(payload, list):
        for item in payload:
            text = _extract_text(item)
            if text:
                return text

    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(payload)


def _last_user(msgs: list[ChatMessage]) -> str:
    for m in reversed(msgs):
        if m.role == "user":
            return m.content
    return "\n\n".join(m.content for m in msgs)


async def _resolve_current_user(
    authorization: str | None = Header(default=None),
    query_key: Annotated[str | None, Security(api_key_query)] = None,
    header_key: Annotated[str | None, Security(api_key_header)] = None,
) -> UserRead:
    """Resolve the LangBuilder user based on OpenAI-style headers.

    OpenAI clients typically send API keys via the Authorization header (Bearer ...)
    while LangBuilder also supports the x-api-key header/query parameter. We accept
    either format and delegate to the shared api_key_security helper.
    """
    bearer_key: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_key = authorization.split(" ", 1)[1].strip()
    token = bearer_key or header_key or query_key
    return await api_key_security(query_key or token, header_key or token)


async def _fetch_accessible_flows(user: UserRead) -> list[Flow]:
    """Return flows that the caller can access via the OpenAI shim."""
    async with session_scope() as session:
        stmt = (
            select(Flow)
            .where(Flow.is_component == False)  # noqa: E712
            .where(
                or_(
                    Flow.user_id == user.id,
                    Flow.access_type == AccessTypeEnum.PUBLIC,
                )
            )
        )
        return list((await session.exec(stmt)).all())


def _model_identifier(flow: Flow, *, include_prefix: bool = True) -> str:
    suffix = flow.endpoint_name or str(flow.id)
    return f"lb:{suffix}" if include_prefix else suffix


def _flow_to_model_payload(flow: Flow) -> dict[str, Any]:
    updated = flow.updated_at
    if isinstance(updated, str):
        try:
            updated_dt = datetime.fromisoformat(updated)
        except ValueError:
            updated_dt = None
    else:
        updated_dt = updated
    created_ts = int(updated_dt.timestamp()) if updated_dt else int(time.time())
    return {
        "id": _model_identifier(flow),
        "object": "model",
        "created": created_ts,
        "owned_by": str(flow.user_id) if flow.user_id else None,
        "root": _model_identifier(flow),
        "parent": None,
        "permission": [],
        "metadata": {
            "display_name": flow.name,
            "description": flow.description,
            "endpoint_name": flow.endpoint_name,
            "flow_id": str(flow.id),
            "access": flow.access_type.value if flow.access_type else AccessTypeEnum.PRIVATE.value,
        },
    }


def _build_flow_lookup(flows: list[Flow]) -> dict[str, FlowRead]:
    lookup: dict[str, FlowRead] = {}
    for flow in flows:
        flow_read = FlowRead.model_validate(flow, from_attributes=True)
        for key in {
            str(flow.id),
            _model_identifier(flow),
            _model_identifier(flow, include_prefix=False),
            f"lb:{flow.id}",
        }:
            lookup[key] = flow_read
    return lookup


def _ensure_flow_access(flow: FlowRead, user: UserRead) -> None:
    if flow.access_type == AccessTypeEnum.PUBLIC:
        return
    if flow.user_id and flow.user_id == user.id:
        return
    raise HTTPException(status_code=403, detail="Flow is not accessible with this API key")


@router.get("/v1/models")
async def list_models(current_user: Annotated[UserRead, Depends(_resolve_current_user)]):
    flows = await _fetch_accessible_flows(current_user)
    if not flows:
        return {"object": "list", "data": []}
    return {"object": "list", "data": [_flow_to_model_payload(flow) for flow in flows]}


@router.post("/v1/chat/completions")
async def chat(req: ChatRequest, current_user: Annotated[UserRead, Depends(_resolve_current_user)]):
    if req.stream:
        # OpenWebUI may set stream=true by default; we currently respond non-streaming.
        req.stream = False  # type: ignore[assignment]
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    flows = await _fetch_accessible_flows(current_user)
    if not flows:
        raise HTTPException(status_code=404, detail="No flows available for this account")

    flow_lookup = _build_flow_lookup(flows)
    requested_model = req.model or _model_identifier(flows[0])
    flow_key = requested_model.split(":", 1)[1] if requested_model.startswith("lb:") else requested_model
    flow_read = flow_lookup.get(requested_model) or flow_lookup.get(flow_key)
    if flow_read is None:
        # attempt to resolve via helper that checks DB + permissions
        target_identifier = flow_key
        flow_read = await get_flow_by_id_or_endpoint_name(target_identifier, user_id=str(current_user.id))
        _ensure_flow_access(flow_read, current_user)
    else:
        _ensure_flow_access(flow_read, current_user)

    prompt = _last_user(req.messages)
    simplified_request = SimplifiedAPIRequest(
        input_value=prompt,
        input_type="chat",
        output_type="chat",
    )
    run_response = await simple_run_flow(flow=flow_read, input_request=simplified_request, api_key_user=current_user)
    lb_json = run_response.model_dump()
    text = _extract_text(lb_json)

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested_model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
