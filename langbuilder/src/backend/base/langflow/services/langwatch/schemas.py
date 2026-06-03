"""Pydantic v2 request/response schemas for the LangWatch usage API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request Models ────────────────────────────────────────────────────────────


class SaveLangWatchKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=500)


class UsageQueryParams(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    user_id: UUID | None = None
    sub_view: Literal["flows", "mcp"] = "flows"


class FlowRunsQueryParams(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=10, ge=1, le=50)


# ── Response Models ───────────────────────────────────────────────────────────


class DateRange(BaseModel):
    from_: date | None = Field(None, alias="from")
    to: date | None = None

    model_config = {"populate_by_name": True}


class UsageSummary(BaseModel):
    total_cost_usd: float
    total_invocations: int
    avg_cost_per_invocation_usd: float
    active_flow_count: int
    date_range: DateRange
    currency: str = "USD"
    data_source: str = "langwatch"
    cached: bool = False
    cache_age_seconds: int | None = None
    truncated: bool = False  # True if > 10,000 traces were encountered


class FlowUsage(BaseModel):
    flow_id: UUID
    flow_name: str
    total_cost_usd: float
    invocation_count: int
    avg_cost_per_invocation_usd: float
    owner_user_id: UUID
    owner_username: str


class UsageResponse(BaseModel):
    summary: UsageSummary
    flows: list[FlowUsage]


class RunDetail(BaseModel):
    run_id: str
    started_at: datetime
    cost_usd: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model: str | None = None
    duration_ms: int | None = None
    status: Literal["success", "error", "partial"] = "success"


class FlowRunsResponse(BaseModel):
    flow_id: UUID
    flow_name: str
    runs: list[RunDetail]
    total_runs_in_period: int


class SaveKeyResponse(BaseModel):
    success: bool
    key_preview: str
    message: str


class KeyStatusResponse(BaseModel):
    has_key: bool
    key_preview: str | None = None
    configured_at: datetime | None = None
