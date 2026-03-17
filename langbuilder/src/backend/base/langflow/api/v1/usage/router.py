"""Usage & Cost Tracking API endpoints.

Implements four endpoints:
  GET  /api/v1/usage/                          — aggregated usage summary
  GET  /api/v1/usage/{flow_id}/runs            — per-run detail for a flow
  POST /api/v1/usage/settings/langwatch-key    — save/validate LangWatch key (admin)
  GET  /api/v1/usage/settings/langwatch-key/status — key status
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.auth.utils import get_current_active_superuser

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.user.model import User
from langflow.services.langwatch.exceptions import (
    LangWatchConnectionError,
    LangWatchError,
    LangWatchInsufficientCreditsError,
    LangWatchInvalidKeyError,
    LangWatchKeyNotConfiguredError,
    LangWatchTimeoutError,
    LangWatchUnavailableError,
)
from langflow.services.langwatch.schemas import (
    FlowRunsQueryParams,
    FlowRunsResponse,
    KeyStatusResponse,
    SaveKeyResponse,
    SaveLangWatchKeyRequest,
    UsageQueryParams,
    UsageResponse,
)
from langflow.services.langwatch.service import LangWatchService, get_langwatch_service

router = APIRouter(prefix="/usage", tags=["Usage & Cost Tracking"])


CurrentSuperUser = Annotated[User, Depends(get_current_active_superuser)]
LangWatchDep = Annotated[LangWatchService, Depends(get_langwatch_service)]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_flow_ids_for_user(
    db: AsyncSession,
    user_id: UUID | None,
) -> set[UUID]:
    """Return the set of flow IDs owned by user_id, or all flow IDs if user_id is None."""
    if user_id is not None:
        result = await db.execute(select(Flow.id).where(Flow.user_id == user_id))
    else:
        result = await db.execute(select(Flow.id))
    return {row[0] for row in result.fetchall()}


async def _get_stored_key_or_raise(langwatch: LangWatchService) -> str:
    """Retrieve stored LangWatch API key or raise 503 KEY_NOT_CONFIGURED."""
    api_key = await langwatch.get_stored_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "KEY_NOT_CONFIGURED",
                "message": "LangWatch API key not configured. Admin setup required.",
                "retryable": False,
            },
        )
    return api_key


def _raise_langwatch_http_error(exc: Exception) -> None:
    """Map LangWatch service exceptions to structured HTTP errors."""
    if isinstance(exc, LangWatchKeyNotConfiguredError):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "KEY_NOT_CONFIGURED",
                "message": "LangWatch API key not configured. Admin setup required.",
                "retryable": False,
            },
        )
    if isinstance(exc, LangWatchTimeoutError):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LANGWATCH_TIMEOUT",
                "message": "LangWatch did not respond within the allowed time. Please try again.",
                "retryable": True,
            },
        )
    if isinstance(exc, (LangWatchUnavailableError, LangWatchConnectionError)):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LANGWATCH_UNAVAILABLE",
                "message": "LangWatch is temporarily unavailable. Please try again.",
                "retryable": True,
            },
        )
    if isinstance(exc, LangWatchInvalidKeyError):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_KEY",
                "message": "Invalid API key. Please check your LangWatch account settings and try again.",
            },
        )
    if isinstance(exc, LangWatchInsufficientCreditsError):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INSUFFICIENT_CREDITS",
                "message": "Your LangWatch account has insufficient credits. Please upgrade your plan at langwatch.ai.",
            },
        )
    raise exc


def _empty_summary(params: UsageQueryParams) -> UsageResponse:
    """Return an empty UsageResponse for the given query params."""
    from langflow.services.langwatch.schemas import DateRange, UsageSummary

    return UsageResponse(
        summary=UsageSummary(
            total_cost_usd=0.0,
            total_invocations=0,
            avg_cost_per_invocation_usd=0.0,
            active_flow_count=0,
            date_range=DateRange(from_=params.from_date, to=params.to_date),
        ),
        flows=[],
    )


# ── Endpoint 1: GET /usage/ ───────────────────────────────────────────────────


@router.get("/", response_model=UsageResponse)
async def get_usage_summary(
    current_user: CurrentActiveUser,
    db: DbSession,
    langwatch: LangWatchDep,
    from_date: Annotated[str | None, Query(description="ISO 8601 start date (YYYY-MM-DD)")] = None,
    to_date: Annotated[str | None, Query(description="ISO 8601 end date (YYYY-MM-DD)")] = None,
    user_id: Annotated[str | None, Query(description="Admin only: filter by user UUID")] = None,
    sub_view: Annotated[str, Query(description="flows | mcp")] = "flows",
) -> UsageResponse:
    """Return aggregated cost and invocation data.

    Non-admin users receive only their own flows (user_id param silently ignored).
    Admins can filter by user_id or retrieve all flows.
    """
    params = UsageQueryParams(
        from_date=from_date,
        to_date=to_date,
        user_id=user_id,
        sub_view=sub_view,
    )

    # ── Ownership Filter Logic ────────────────────────────────────────────────
    # Non-admins: always own flows only (params.user_id silently ignored)
    # Admin with user_id: filter to that user's flows
    # Admin without user_id: all flows
    if current_user.is_superuser and params.user_id:
        effective_user_id: UUID | None = params.user_id
    elif current_user.is_superuser:
        effective_user_id = None  # Admin sees all
    else:
        effective_user_id = current_user.id  # Non-admin: own flows only

    allowed_flow_ids = await _get_flow_ids_for_user(db, effective_user_id)

    api_key = await _get_stored_key_or_raise(langwatch)
    org_id = "default"  # Single-org deployment — cache shared across users of same org

    try:
        return await langwatch.get_usage_summary(
            params, allowed_flow_ids, api_key, org_id,
            is_admin=current_user.is_superuser,
        )
    except LangWatchError as exc:
        _raise_langwatch_http_error(exc)
    return _empty_summary(params)  # pragma: no cover — unreachable, satisfies type checker


# ── Endpoint 2: GET /usage/{flow_id}/runs ────────────────────────────────────


@router.get("/{flow_id}/runs", response_model=FlowRunsResponse)
async def get_flow_runs(
    flow_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    langwatch: LangWatchDep,
    from_date: Annotated[str | None, Query(description="ISO 8601 start date")] = None,
    to_date: Annotated[str | None, Query(description="ISO 8601 end date")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Max number of runs to return")] = 10,
) -> FlowRunsResponse:
    """Return per-run detail for a specific flow.

    Non-admins can only access flows they own (returns 403 otherwise).
    """
    query = FlowRunsQueryParams(from_date=from_date, to_date=to_date, limit=limit)

    # Ownership check — look up flow in DB
    result = await db.execute(select(Flow.id, Flow.name, Flow.user_id).where(Flow.id == flow_id))
    row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "FLOW_NOT_FOUND",
                "message": "No usage data found for this flow in the selected period.",
            },
        )

    flow_name: str = row[1]
    flow_owner_id: UUID = row[2]

    # Non-admin accessing another user's flow → 403
    if not current_user.is_superuser and flow_owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "You do not have permission to view this flow's usage data.",
            },
        )

    api_key = await _get_stored_key_or_raise(langwatch)

    try:
        return await langwatch.fetch_flow_runs(
            flow_id=flow_id,
            flow_name=flow_name,
            query=query,
            api_key=api_key,
        )
    except LangWatchError as exc:
        _raise_langwatch_http_error(exc)
    # pragma: no cover — unreachable
    return FlowRunsResponse(flow_id=flow_id, flow_name=flow_name, runs=[], total_runs_in_period=0)


# ── Endpoint 3: POST /usage/settings/langwatch-key ───────────────────────────


@router.post("/settings/langwatch-key", response_model=SaveKeyResponse)
async def save_langwatch_key(
    body: SaveLangWatchKeyRequest,
    current_user: CurrentSuperUser,
    langwatch: LangWatchDep,
) -> SaveKeyResponse:
    """Validate the provided LangWatch API key and store it.

    Admin only. Returns 403 if the requesting user is not a superuser.
    """
    api_key = body.api_key.strip()

    # Validate key against LangWatch before saving
    try:
        is_valid = await langwatch.validate_key(api_key)
    except LangWatchConnectionError as exc:
        _raise_langwatch_http_error(exc)
        return SaveKeyResponse(success=False, key_preview="", message="")  # pragma: no cover

    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_KEY",
                "message": "Invalid API key. Please check your LangWatch account settings and try again.",
            },
        )

    await langwatch.save_key(api_key, current_user.id)

    _preview_len = 3
    preview = f"****{api_key[-_preview_len:]}" if len(api_key) > _preview_len else "****"
    return SaveKeyResponse(
        success=True,
        key_preview=preview,
        message="LangWatch API key validated and saved successfully.",
    )


# ── Endpoint 4: GET /usage/settings/langwatch-key/status ─────────────────────


@router.get("/settings/langwatch-key/status", response_model=KeyStatusResponse)
async def get_langwatch_key_status(
    _current_user: CurrentSuperUser,
    langwatch: LangWatchDep,
) -> KeyStatusResponse:
    """Return whether a LangWatch API key is configured. Admin only."""
    return await langwatch.get_key_status()
