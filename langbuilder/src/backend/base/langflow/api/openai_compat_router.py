"""OpenAI-compatible shim for Langflow.

Exposes:
  GET  /v1/models              — lists all flows the caller can access
  POST /v1/chat/completions    — runs a flow, returns an OpenAI-shaped response

This allows OpenWebUI (and any other OpenAI-compatible client) to point its
"OpenAI API" connection directly at Langflow using a Langflow API key.

Usage in OpenWebUI:
  Admin Panel → Settings → Connections → + Add OpenAI connection
    URL: http://host.docker.internal:7861
    API Key: <langflow api key from Settings → API Keys>
"""
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

from langflow.api.v1.endpoints import simple_run_flow
from langflow.api.v1.schemas import SimplifiedAPIRequest
from langflow.helpers.flow import get_flow_by_id_or_endpoint_name
from langflow.services.auth.utils import api_key_header, api_key_query, api_key_security
from langflow.services.database.models.flow.model import AccessTypeEnum, Flow, FlowRead
from langflow.services.deps import session_scope

if TYPE_CHECKING:
    from langflow.services.database.models.user.model import UserRead
else:
    UserRead = Any

router = APIRouter(tags=["OpenAI-Compatible"])


# --- request / response models ---

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = 0.2
    stream: bool | None = False
    max_tokens: int | None = None


# --- helpers ---

def _extract_text(payload: Any) -> str:
    """Extract a human-readable string from a Langflow run response."""
    if isinstance(payload, str):
        return payload

    def ensure_text(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        return None

    def best_from_message(msg: Any) -> str | None:
        if isinstance(msg, dict):
            for candidate in [
                msg.get("message"),
                msg.get("text"),
                msg.get("data", {}).get("text") if isinstance(msg.get("data"), dict) else None,
            ]:
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
        for run_output in payload.get("outputs") or []:
            if not isinstance(run_output, dict):
                continue
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
    """Accept OpenAI-style Bearer tokens as well as x-api-key headers."""
    bearer_key: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_key = authorization.split(" ", 1)[1].strip()
    token = bearer_key or header_key or query_key
    return await api_key_security(query_key or token, header_key or token)


async def _fetch_accessible_flows(user: UserRead) -> list[Flow]:
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


def _model_id(flow: Flow) -> str:
    suffix = flow.endpoint_name or str(flow.id)
    return f"lb:{suffix}"


def _flow_to_model(flow: Flow) -> dict[str, Any]:
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
        "id": _model_id(flow),
        "object": "model",
        "created": created_ts,
        "owned_by": str(flow.user_id) if flow.user_id else "langflow",
        "name": flow.name,
        "metadata": {
            "display_name": flow.name,
            "description": flow.description,
            "endpoint_name": flow.endpoint_name,
            "flow_id": str(flow.id),
        },
    }


def _build_lookup(flows: list[Flow]) -> dict[str, FlowRead]:
    lookup: dict[str, FlowRead] = {}
    for flow in flows:
        flow_read = FlowRead.model_validate(flow, from_attributes=True)
        for key in {str(flow.id), _model_id(flow), flow.endpoint_name or "", f"lb:{flow.id}"}:
            if key:
                lookup[key] = flow_read
    return lookup


# --- endpoints ---

@router.get("/v1/models")
async def list_models(current_user: Annotated[UserRead, Depends(_resolve_current_user)]):
    flows = await _fetch_accessible_flows(current_user)
    return {"object": "list", "data": [_flow_to_model(f) for f in flows]}


@router.post("/v1/chat/completions")
async def chat_completions(
    req: ChatRequest,
    current_user: Annotated[UserRead, Depends(_resolve_current_user)],
):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    flows = await _fetch_accessible_flows(current_user)
    if not flows:
        raise HTTPException(status_code=404, detail="No flows accessible with this API key")

    lookup = _build_lookup(flows)
    model = req.model or _model_id(flows[0])
    flow_key = model.split(":", 1)[1] if model.startswith("lb:") else model
    flow_read = lookup.get(model) or lookup.get(flow_key)

    if flow_read is None:
        flow_read = await get_flow_by_id_or_endpoint_name(flow_key, user_id=str(current_user.id))
        if flow_read is None:
            raise HTTPException(status_code=404, detail=f"Flow '{model}' not found")

    result = await simple_run_flow(
        flow=flow_read,
        input_request=SimplifiedAPIRequest(
            input_value=_last_user(req.messages),
            input_type="chat",
            output_type="chat",
        ),
        api_key_user=current_user,
    )
    text = _extract_text(result.model_dump())

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
