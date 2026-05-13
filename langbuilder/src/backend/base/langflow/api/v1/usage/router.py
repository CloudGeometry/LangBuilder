"""Usage & Cost Tracking API endpoints.

Implements four endpoints:
  GET  /api/v1/usage/                          — aggregated usage summary
  GET  /api/v1/usage/{flow_id}/runs            — per-run detail for a flow
  POST /api/v1/usage/settings/langwatch-key    — save/validate LangWatch key (admin)
  GET  /api/v1/usage/settings/langwatch-key/status — key status
"""
from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid5, NAMESPACE_DNS

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


# ── Demo Mode Helpers ─────────────────────────────────────────────────────────

_DEMO_MODE = os.getenv("USAGE_DEMO_MODE", "").lower() == "true"


async def _generate_demo_summary(
    params: UsageQueryParams,
    db: "AsyncSession",
    current_user: User,
) -> UsageResponse:
    """Generate realistic multi-day mock usage data using real flow names from DB."""
    from langflow.services.langwatch.schemas import (
        DailyCost,
        DateRange,
        FlowUsage,
        UsageSummary,
    )

    # Query real flows from DB (with ownership filtering)
    if current_user.is_superuser and not params.user_id:
        stmt = select(Flow.id, Flow.name, Flow.user_id, User.username).join(
            User, Flow.user_id == User.id, isouter=True
        ).where(Flow.user_id.isnot(None))
    elif current_user.is_superuser and params.user_id:
        stmt = select(Flow.id, Flow.name, Flow.user_id, User.username).join(
            User, Flow.user_id == User.id, isouter=True
        ).where(Flow.user_id == params.user_id)
    else:
        stmt = select(Flow.id, Flow.name, Flow.user_id, User.username).join(
            User, Flow.user_id == User.id, isouter=True
        ).where(Flow.user_id == current_user.id)

    result = await db.execute(stmt)
    rows = result.fetchall()
    if not rows:
        return _empty_summary(params)

    # Date range
    end = params.to_date or date.today()
    start = params.from_date or (end - timedelta(days=30))
    if (end - start).days > 366:
        start = end - timedelta(days=366)

    # Seed random for deterministic output
    seed_str = f"{start}:{end}:{params.sub_view}:{params.user_id}"
    rng = random.Random(seed_str)

    # Assign each flow a "popularity weight" (power law)
    flow_weights = {}
    for row in rows:
        flow_weights[row.id] = rng.paretovariate(1.5)
    total_weight = sum(flow_weights.values())

    # Generate daily data
    day_totals: dict[date, dict] = {}
    flow_totals: dict[UUID, dict] = {
        r.id: {"name": r.name, "user_id": r.user_id or UUID(int=0),
               "username": r.username or "", "cost": 0.0, "count": 0}
        for r in rows
    }

    d = start
    while d <= end:
        # Weekday/weekend multiplier
        weekday = d.weekday()
        day_mult = 1.0 if weekday < 5 else (0.3 if weekday == 5 else 0.1)
        day_mult *= rng.uniform(0.7, 1.3)  # daily variation

        day_cost = 0.0
        day_count = 0

        for row in rows:
            weight = flow_weights[row.id] / total_weight
            # Invocations: proportional to weight, scaled by day multiplier
            invocations = max(0, int(rng.gauss(weight * 30, weight * 10) * day_mult))
            if invocations == 0 and rng.random() < 0.3:
                invocations = rng.randint(1, 3)  # some minimum activity

            # Cost per invocation: $0.008 - $0.04 (Opus range)
            cost = sum(rng.uniform(0.008, 0.04) for _ in range(invocations))

            flow_totals[row.id]["cost"] += cost
            flow_totals[row.id]["count"] += invocations
            day_cost += cost
            day_count += invocations

        day_totals[d] = {"cost": round(day_cost, 6), "count": day_count}
        d += timedelta(days=1)

    # Build daily_costs
    daily_costs = [
        DailyCost(date=d, cost_usd=v["cost"], invocations=v["count"])
        for d, v in sorted(day_totals.items())
    ]

    # Build flow usages
    flow_usages = [
        FlowUsage(
            flow_id=fid,
            flow_name=ft["name"],
            total_cost_usd=round(ft["cost"], 6),
            invocation_count=ft["count"],
            avg_cost_per_invocation_usd=round(ft["cost"] / ft["count"], 6) if ft["count"] > 0 else 0.0,
            owner_user_id=ft["user_id"],
            owner_username=ft["username"],
        )
        for fid, ft in flow_totals.items()
        if ft["count"] > 0
    ]
    flow_usages.sort(key=lambda f: f.total_cost_usd, reverse=True)

    total_cost = sum(f.total_cost_usd for f in flow_usages)
    total_inv = sum(f.invocation_count for f in flow_usages)

    return UsageResponse(
        summary=UsageSummary(
            total_cost_usd=round(total_cost, 6),
            total_invocations=total_inv,
            avg_cost_per_invocation_usd=round(total_cost / total_inv, 6) if total_inv > 0 else 0.0,
            active_flow_count=len(flow_usages),
            date_range=DateRange(from_=start, to=end),
        ),
        flows=flow_usages,
        daily_costs=daily_costs,
    )


def _generate_demo_runs(flow_id: UUID, flow_name: str, query: FlowRunsQueryParams) -> FlowRunsResponse:
    """Generate mock run details for a flow drill-down."""
    from langflow.services.langwatch.schemas import RunDetail

    end = query.to_date or date.today()
    start = query.from_date or (end - timedelta(days=30))

    rng = random.Random(f"{flow_id}:{start}:{end}")
    runs = []

    for i in range(query.limit):
        # Spread runs across the date range
        day_offset = rng.randint(0, max(0, (end - start).days))
        run_date = start + timedelta(days=day_offset)
        hour = rng.randint(8, 18)
        minute = rng.randint(0, 59)
        started_at = datetime(run_date.year, run_date.month, run_date.day,
                              hour, minute, rng.randint(0, 59), tzinfo=timezone.utc)

        input_tokens = rng.randint(500, 5000)
        output_tokens = rng.randint(200, 3000)
        cost = round(input_tokens * 0.000015 + output_tokens * 0.000075, 6)
        status = "error" if rng.random() < 0.05 else "success"

        runs.append(RunDetail(
            run_id=str(uuid5(NAMESPACE_DNS, f"demo-run-{flow_id}-{i}")),
            started_at=started_at,
            cost_usd=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model="anthropic/claude-opus-4",
            duration_ms=rng.randint(2000, 15000),
            status=status,
        ))

    runs.sort(key=lambda r: r.started_at, reverse=True)

    total_in_period = rng.randint(query.limit, query.limit * 5)

    return FlowRunsResponse(
        flow_id=flow_id,
        flow_name=flow_name,
        runs=runs,
        total_runs_in_period=total_in_period,
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

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    if _DEMO_MODE:
        return await _generate_demo_summary(params, db, current_user)

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

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    if _DEMO_MODE:
        result = await db.execute(select(Flow.name).where(Flow.id == flow_id))
        row = result.fetchone()
        return _generate_demo_runs(flow_id, row[0] if row else "Unknown Flow", query)

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
