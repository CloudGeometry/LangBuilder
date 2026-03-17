"""Tests for F2-T3: _fetch_from_langwatch() and _fetch_all_pages() in LangWatchService.

Covers all 10 acceptance criteria:
1. _fetch_from_langwatch(params, api_key) is async and returns list[dict]
2. Converts from_date/to_date to epoch milliseconds for the API request
3. Sends X-Auth-Token: <api_key> header on each request
4. Uses POST /api/traces/search with startDate, endDate, pageSize in JSON body
5. _fetch_all_pages() follows scroll pagination: sends scrollId in subsequent requests
6. Stops pagination when scrollId is null/absent in response
7. Truncation guard: stops after MAX_PAGES = 10 pages
8. Stops pagination when a page returns 0 traces
9. Combines all pages into a single flat list[dict] and returns it
10. response.raise_for_status() called so HTTP errors propagate as httpx.HTTPStatusError
"""
from __future__ import annotations

import inspect
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx
import pytest
from langflow.services.langwatch.exceptions import (
    LangWatchInvalidKeyError,
    LangWatchUnavailableError,
)
from langflow.services.langwatch.schemas import UsageQueryParams
from langflow.services.langwatch.service import MAX_PAGES, PAGE_SIZE, LangWatchService

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def service():
    """Instantiate LangWatchService bypassing DI."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = MagicMock()
    svc._client = LangWatchService._create_httpx_client()
    return svc


@pytest.fixture
def query_params():
    """Sample UsageQueryParams for testing."""
    return UsageQueryParams(
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 31),
        sub_view="flows",
    )


SEARCH_URL = "https://app.langwatch.ai/api/traces/search"
API_KEY = "test-api-key-12345"


# ── AC1: _fetch_from_langwatch is async and returns list[dict] ────────────────


def test_fetch_from_langwatch_is_async():
    """_fetch_from_langwatch must be an async method."""
    assert inspect.iscoroutinefunction(LangWatchService._fetch_from_langwatch), (
        "_fetch_from_langwatch must be an async method"
    )


def test_fetch_all_pages_is_async():
    """_fetch_all_pages must be an async method."""
    assert inspect.iscoroutinefunction(LangWatchService._fetch_all_pages), (
        "_fetch_all_pages must be an async method"
    )


@pytest.mark.asyncio
async def test_fetch_from_langwatch_returns_list(service, query_params, httpx_mock: HTTPXMock):
    """_fetch_from_langwatch returns a list[dict]."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [{"trace_id": "abc"}], "pagination": {"totalHits": 1, "scrollId": None}},
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)
    assert isinstance(result, list)
    assert all(isinstance(t, dict) for t in result)


# ── AC2: Converts from_date/to_date to epoch milliseconds ────────────────────


@pytest.mark.asyncio
async def test_fetch_converts_dates_to_milliseconds(service, httpx_mock: HTTPXMock):
    """from_date and to_date are converted to epoch milliseconds in the request body."""
    from_dt = date(2024, 1, 1)
    to_dt = date(2024, 1, 31)
    params = UsageQueryParams(from_date=from_dt, to_date=to_dt)

    # Expected ms: convert date to datetime at midnight UTC, then to ms
    expected_start_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected_end_ms = int(datetime(2024, 1, 31, tzinfo=timezone.utc).timestamp() * 1000)

    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )
    await service._fetch_from_langwatch(params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    import json
    body = json.loads(requests[0].content)
    assert body["startDate"] == expected_start_ms
    assert body["endDate"] == expected_end_ms


# ── AC3: Sends X-Auth-Token header ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_sends_auth_header(service, query_params, httpx_mock: HTTPXMock):
    """X-Auth-Token header is sent with each request."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )
    await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) >= 1
    for req in requests:
        assert req.headers.get("x-auth-token") == API_KEY, (
            "X-Auth-Token header must be present on every request"
        )


# ── AC4: POST /api/traces/search with correct body fields ────────────────────


@pytest.mark.asyncio
async def test_fetch_uses_post_with_correct_body_fields(service, query_params, httpx_mock: HTTPXMock):
    """POST /api/traces/search with startDate, endDate, pageSize in body."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )
    await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    import json
    body = json.loads(req.content)
    assert "startDate" in body
    assert "endDate" in body
    assert "pageSize" in body
    assert body["pageSize"] == PAGE_SIZE


# ── AC5: Scroll pagination — scrollId sent in subsequent requests ─────────────


@pytest.mark.asyncio
async def test_fetch_multiple_pages_sends_scroll_id(service, query_params, httpx_mock: HTTPXMock):
    """Second request includes scrollId from first response."""
    scroll_id = "scroll-token-xyz"
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t1"}],
            "pagination": {"totalHits": 2, "scrollId": scroll_id},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t2"}],
            "pagination": {"totalHits": 2, "scrollId": None},
        },
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    import json
    first_body = json.loads(requests[0].content)
    second_body = json.loads(requests[1].content)
    # First request should NOT have scrollId
    assert "scrollId" not in first_body or first_body.get("scrollId") is None
    # Second request must include scrollId
    assert second_body.get("scrollId") == scroll_id
    assert len(result) == 2


# ── AC6: Stops when scrollId is null/absent ───────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_stops_when_scroll_id_null(service, query_params, httpx_mock: HTTPXMock):
    """Stops after final page where scrollId is null."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t1"}, {"trace_id": "t2"}],
            "pagination": {"totalHits": 2, "scrollId": None},
        },
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, "Should stop after one page when scrollId is None"
    assert len(result) == 2


@pytest.mark.asyncio
async def test_fetch_stops_when_scroll_id_absent(service, query_params, httpx_mock: HTTPXMock):
    """Stops when scrollId is absent from the pagination object."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t1"}],
            "pagination": {"totalHits": 1},
        },
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, "Should stop when scrollId is absent"
    assert len(result) == 1


# ── AC7: Truncation guard — stops after MAX_PAGES ─────────────────────────────


def test_max_pages_constant():
    """MAX_PAGES constant is 10."""
    assert MAX_PAGES == 10


@pytest.mark.asyncio
async def test_fetch_truncation_guard(service, query_params, httpx_mock: HTTPXMock):
    """Stops after MAX_PAGES even if scrollId keeps coming back."""
    # Add MAX_PAGES responses each with a scrollId
    for i in range(MAX_PAGES):
        httpx_mock.add_response(
            method="POST",
            url=SEARCH_URL,
            json={
                "traces": [{"trace_id": f"t{i}"}],
                "pagination": {"totalHits": 9999, "scrollId": f"scroll-{i}"},
            },
        )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == MAX_PAGES, f"Should stop after {MAX_PAGES} pages"
    assert len(result) == MAX_PAGES


# ── AC8: Stops when a page returns 0 traces ───────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_stops_on_empty_page(service, query_params, httpx_mock: HTTPXMock):
    """Stops when a page returns 0 traces even if scrollId is present."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t1"}],
            "pagination": {"totalHits": 10, "scrollId": "scroll-1"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [],
            "pagination": {"totalHits": 10, "scrollId": "scroll-2"},
        },
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    requests = httpx_mock.get_requests()
    assert len(requests) == 2, "Should stop after empty page"
    assert len(result) == 1


# ── AC9: Combines all pages into a single flat list ───────────────────────────


@pytest.mark.asyncio
async def test_fetch_combines_pages_into_flat_list(service, query_params, httpx_mock: HTTPXMock):
    """All pages combined into a single flat list."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t1"}, {"trace_id": "t2"}],
            "pagination": {"totalHits": 4, "scrollId": "scroll-1"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [{"trace_id": "t3"}, {"trace_id": "t4"}],
            "pagination": {"totalHits": 4, "scrollId": None},
        },
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)

    assert len(result) == 4
    trace_ids = [t["trace_id"] for t in result]
    assert trace_ids == ["t1", "t2", "t3", "t4"]


# ── AC10: raise_for_status() called — HTTP errors propagate ──────────────────


@pytest.mark.asyncio
async def test_fetch_raises_on_http_401(service, query_params, httpx_mock: HTTPXMock):
    """HTTP 401 raises httpx.HTTPStatusError."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=401,
        json={"error": "Unauthorized", "message": "Invalid auth token."},
    )
    with pytest.raises(LangWatchInvalidKeyError):
        await service._fetch_from_langwatch(query_params, API_KEY)


@pytest.mark.asyncio
async def test_fetch_raises_on_http_500(service, query_params, httpx_mock: HTTPXMock):
    """HTTP 500 raises LangWatchUnavailableError."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=500,
        json={"error": "Internal Server Error", "message": "Something went wrong."},
    )
    with pytest.raises(LangWatchUnavailableError):
        await service._fetch_from_langwatch(query_params, API_KEY)


# ── Bonus: single page fetch works end-to-end ────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_single_page(service, query_params, httpx_mock: HTTPXMock):
    """Single page (no scrollId) returns traces from that page."""
    traces = [{"trace_id": "t1", "metrics": {"total_cost": 0.01}}]
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 1, "scrollId": None}},
    )
    result = await service._fetch_from_langwatch(query_params, API_KEY)
    assert result == traces
