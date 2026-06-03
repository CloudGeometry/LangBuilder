"""Tests for F2-T9: fetch_flow_runs() in LangWatchService.

Covers acceptance criteria:
1. fetch_flow_runs_returns_list — returns list of flow run records for a flow_id
2. fetch_flow_runs_filters_by_flow_id — only returns runs for the specified flow_id
3. fetch_flow_runs_empty_result — returns empty list when no runs found
4. fetch_flow_runs_date_range_filtering — date range params are passed to API correctly
5. fetch_flow_runs_pagination — handles multiple pages
6. fetch_flow_runs_handles_api_error — raises LangWatchUnavailableError on network failure
7. fetch_flow_runs_filters_by_flow_name — only returns traces matching the flow name label

Note: Ownership enforcement (admin/non-admin access) is handled by the router,
not by fetch_flow_runs. See test_flow_runs_endpoint.py and test_usage_security.py
for ownership tests.
"""
from __future__ import annotations

import inspect
from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest
from langflow.services.langwatch.exceptions import LangWatchUnavailableError
from langflow.services.langwatch.schemas import FlowRunsQueryParams, FlowRunsResponse
from langflow.services.langwatch.service import LangWatchService

SEARCH_URL = "https://app.langwatch.ai/api/traces/search"
API_KEY = "test-api-key-12345"

FLOW_ID = UUID("3f4a9b12-0000-0000-0000-000000000001")
FLOW_NAME = "Customer Support Bot"
OTHER_FLOW_ID = UUID("7c8d2e34-0000-0000-0000-000000000002")
OTHER_FLOW_NAME = "Invoice Generator"

USER_ID = UUID("a1b2c3d4-0000-0000-0000-000000000001")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_trace(
    trace_id: str,
    flow_name: str,
    cost: float = 0.005,
    started_ms: int = 1742135520000,
    *,
    has_error: bool = False,
) -> dict:
    """Build a minimal LangWatch trace dict for testing."""
    return {
        "trace_id": trace_id,
        "project_id": "proj_test",
        "metadata": {
            "labels": [f"Flow: {flow_name}"],
            "user_id": "user-test",
        },
        "timestamps": {
            "started_at": started_ms,
            "inserted_at": started_ms + 1000,
            "updated_at": started_ms + 2000,
        },
        "metrics": {
            "total_time_ms": 2340,
            "prompt_tokens": 1240,
            "completion_tokens": 380,
            "total_cost": cost,
        },
        "error": {"message": "error"} if has_error else None,
        "spans": [
            {
                "span_id": f"span_{trace_id}",
                "type": "llm",
                "model": "gpt-4o",
            }
        ],
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def service():
    """Instantiate LangWatchService bypassing DI."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = MagicMock()
    svc.redis = None
    svc._client = LangWatchService._create_httpx_client()
    return svc


@pytest.fixture
def flow_runs_params():
    """Default FlowRunsQueryParams."""
    return FlowRunsQueryParams(
        from_date=date(2026, 3, 1),
        to_date=date(2026, 3, 16),
        limit=10,
    )


# ── AC1: fetch_flow_runs is async and returns FlowRunsResponse ────────────────


def test_fetch_flow_runs_is_async():
    """fetch_flow_runs must be an async method."""
    assert inspect.iscoroutinefunction(LangWatchService.fetch_flow_runs), (
        "fetch_flow_runs must be an async method"
    )


@pytest.mark.asyncio
async def test_fetch_flow_runs_returns_list(service, flow_runs_params, httpx_mock):
    """fetch_flow_runs returns a FlowRunsResponse with a list of runs."""
    # Two traces for target flow
    traces = [
        _make_trace("t1", FLOW_NAME, cost=0.005, started_ms=1742135520000),
        _make_trace("t2", FLOW_NAME, cost=0.004, started_ms=1742135530000),
    ]
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 2, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    assert isinstance(response, FlowRunsResponse)
    assert isinstance(response.runs, list)
    assert len(response.runs) >= 1


# ── AC2: fetch_flow_runs_filters_by_flow_id ───────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_filters_by_flow_id(service, flow_runs_params, httpx_mock):
    """Only returns runs for the specified flow_id, not other flows."""
    # Mix of traces from two different flows
    traces = [
        _make_trace("t1", FLOW_NAME, cost=0.005),
        _make_trace("t2", OTHER_FLOW_NAME, cost=0.003),
        _make_trace("t3", FLOW_NAME, cost=0.004),
    ]
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 3, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    # All returned runs should belong to the target flow
    assert response.flow_id == FLOW_ID
    assert response.flow_name == FLOW_NAME
    # Only traces for FLOW_NAME should be returned (t1 and t3)
    assert len(response.runs) == 2


# ── AC3: fetch_flow_runs_empty_result ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_empty_result(service, flow_runs_params, httpx_mock):
    """Returns FlowRunsResponse with empty runs list when no runs found."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    assert isinstance(response, FlowRunsResponse)
    assert response.runs == []
    assert response.total_runs_in_period == 0


# ── AC4: fetch_flow_runs_date_range_filtering ─────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_date_range_filtering(service, httpx_mock):
    """Date range params (from_date, to_date) are correctly passed to LangWatch API."""
    from_dt = date(2026, 3, 1)
    to_dt = date(2026, 3, 16)
    expected_start_ms = int(datetime(2026, 3, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected_end_ms = int(datetime(2026, 3, 16, tzinfo=timezone.utc).timestamp() * 1000)

    params = FlowRunsQueryParams(from_date=from_dt, to_date=to_dt, limit=10)

    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )

    await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=params,
        api_key=API_KEY,
    )

    import json

    requests = httpx_mock.get_requests()
    assert len(requests) >= 1
    body = json.loads(requests[0].content)
    assert body["startDate"] == expected_start_ms
    assert body["endDate"] == expected_end_ms


# ── AC5: fetch_flow_runs_pagination ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_pagination(service, flow_runs_params, httpx_mock):
    """Handles multiple pages of results via scroll pagination."""
    # Page 1 with scroll_id
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t1", FLOW_NAME)],
            "pagination": {"totalHits": 2, "scrollId": "scroll-123"},
        },
    )
    # Page 2 — no more scroll
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t2", FLOW_NAME)],
            "pagination": {"totalHits": 2, "scrollId": None},
        },
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 2, "Should have fetched two pages"
    assert len(response.runs) == 2


# ── AC6: fetch_flow_runs_handles_api_error ───────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_handles_api_error(service, flow_runs_params, httpx_mock):
    """Raises LangWatchUnavailableError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with pytest.raises(LangWatchUnavailableError):
        await service.fetch_flow_runs(
            flow_id=FLOW_ID,
            flow_name=FLOW_NAME,
            query=flow_runs_params,
            api_key=API_KEY,
        )


@pytest.mark.asyncio
async def test_fetch_flow_runs_handles_timeout(service, flow_runs_params, httpx_mock):
    """Raises LangWatchUnavailableError on timeout."""
    httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))

    with pytest.raises(LangWatchUnavailableError):
        await service.fetch_flow_runs(
            flow_id=FLOW_ID,
            flow_name=FLOW_NAME,
            query=flow_runs_params,
            api_key=API_KEY,
        )


# ── AC7: fetch_flow_runs filters traces by flow name label ──────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_filters_by_flow_name_label(service, flow_runs_params, httpx_mock):
    """Only returns traces whose label matches the target flow name."""
    # Traces for both target flow and another flow
    traces = [
        _make_trace("t1", FLOW_NAME, cost=0.005),
        _make_trace("t2", OTHER_FLOW_NAME, cost=0.003),
    ]
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 2, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    # Should only return runs for the target flow name
    assert response.flow_id == FLOW_ID
    assert len(response.runs) == 1
    assert response.runs[0].run_id == "t1"


@pytest.mark.asyncio
async def test_fetch_flow_runs_returns_all_matching_traces(service, flow_runs_params, httpx_mock):
    """Returns all traces matching the flow name, regardless of caller identity."""
    traces = [
        _make_trace("t1", FLOW_NAME, cost=0.005),
    ]
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 1, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    assert isinstance(response, FlowRunsResponse)
    assert response.flow_id == FLOW_ID


# ── RunDetail fields validation ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_flow_runs_run_detail_fields(service, flow_runs_params, httpx_mock):
    """RunDetail objects in response contain required fields."""
    trace = _make_trace("trace_abc", FLOW_NAME, cost=0.0055, started_ms=1742135520000)
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [trace], "pagination": {"totalHits": 1, "scrollId": None}},
    )

    response = await service.fetch_flow_runs(
        flow_id=FLOW_ID,
        flow_name=FLOW_NAME,
        query=flow_runs_params,
        api_key=API_KEY,
    )

    assert len(response.runs) == 1
    run = response.runs[0]
    assert run.run_id == "trace_abc"
    assert isinstance(run.started_at, datetime)
    assert run.cost_usd == pytest.approx(0.0055)
    assert run.model == "gpt-4o"
