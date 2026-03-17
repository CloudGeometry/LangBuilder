"""F2-T10: Integration tests for the LangWatch service layer.

Tests scenarios NOT covered by individual task tests:
- Full pipeline: fetch → cache → second call uses cache
- Handles empty response gracefully (empty data, no crash)
- Concurrent requests for the same user (mock multiple calls)
- Key lifecycle: save → validate → status → cache invalidation sequence
- Ownership isolation: admin sees all flows, user sees only their own
- Large dataset pagination: simulate 3+ pages of results
- All API calls include the Authorization/X-Auth-Token header
- 429/503 responses propagate correctly (no retry in service → HTTP error)

Uses pytest-httpx for HTTP mocking where applicable, unittest.mock otherwise.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
from langflow.services.langwatch.schemas import (
    DateRange,
    FlowRunsQueryParams,
    FlowUsage,
    UsageQueryParams,
    UsageResponse,
    UsageSummary,
)
from langflow.services.langwatch.service import LangWatchService

# ── Constants ─────────────────────────────────────────────────────────────────

SEARCH_URL = "https://app.langwatch.ai/api/traces/search"
ANALYTICS_URL = "https://app.langwatch.ai/api/analytics/usage"

FLOW_UUID_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
FLOW_UUID_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
FLOW_UUID_C = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
USER_UUID_A = UUID("11111111-1111-1111-1111-111111111111")
USER_UUID_B = UUID("22222222-2222-2222-2222-222222222222")
ADMIN_UUID = UUID("aaaaaaaa-0000-0000-0000-000000000001")

API_KEY = "sk-integration-test-key"
ORG_ID = "org-integration"

SAMPLE_PARAMS = UsageQueryParams(
    from_date=date(2026, 1, 1),
    to_date=date(2026, 1, 31),
    sub_view="flows",
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_trace(
    trace_id: str,
    flow_name: str,
    cost: float = 0.005,
    started_ms: int = 1742135520000,
    *,
    has_error: bool = False,
) -> dict:
    """Build a minimal LangWatch trace dict."""
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
        },
        "metrics": {
            "total_time_ms": 1500,
            "prompt_tokens": 500,
            "completion_tokens": 150,
            "total_cost": cost,
        },
        "error": {"message": "error"} if has_error else None,
        "spans": [{"span_id": f"span_{trace_id}", "type": "llm", "model": "gpt-4o"}],
    }


def _make_usage_response(*, cached: bool = False) -> UsageResponse:
    summary = UsageSummary(
        total_cost_usd=0.01,
        total_invocations=2,
        avg_cost_per_invocation_usd=0.005,
        active_flow_count=1,
        date_range=DateRange(from_=date(2026, 1, 1), to=date(2026, 1, 31)),
        cached=cached,
    )
    flow = FlowUsage(
        flow_id=FLOW_UUID_A,
        flow_name="Alpha Bot",
        total_cost_usd=0.01,
        invocation_count=2,
        avg_cost_per_invocation_usd=0.005,
        owner_user_id=USER_UUID_A,
        owner_username="alice",
    )
    return UsageResponse(summary=summary, flows=[flow])


@pytest.fixture
def redis_mock():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.ttl = AsyncMock(return_value=200)
    r.keys = AsyncMock(return_value=[])
    r.delete = AsyncMock()
    return r


@pytest.fixture
def service_with_redis(redis_mock):
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = redis_mock
    return svc


@pytest.fixture
def service_no_redis():
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = None
    return svc


# ── Test 1: Full pipeline fetch → cache → second call uses cache ──────────────


@pytest.mark.asyncio
async def test_service_full_pipeline_fetch_and_cache(service_with_redis, redis_mock):
    """Full pipeline: first call fetches from LangWatch and caches; second returns cached."""
    cached_response = _make_usage_response(cached=False)

    # First call: cache miss → fetch → write to Redis
    redis_mock.get = AsyncMock(return_value=None)

    with (
        patch.object(
            service_with_redis, "_fetch_from_langwatch", new=AsyncMock(return_value=[])
        ) as mock_fetch,
        patch.object(
            service_with_redis,
            "_filter_by_ownership",
            new=AsyncMock(return_value=([], {})),
        ),
        patch.object(
            service_with_redis,
            "_aggregate_with_metadata",
            return_value=cached_response,
        ),
    ):
        first_result = await service_with_redis.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids={FLOW_UUID_A},
            api_key=API_KEY,
            org_id=ORG_ID,
        )
        mock_fetch.assert_called_once()
        redis_mock.setex.assert_called_once()
        assert first_result is not None

    # Second call: cache hit → return cached data
    redis_mock.get = AsyncMock(return_value=cached_response.model_dump_json().encode())
    redis_mock.ttl = AsyncMock(return_value=250)

    second_result = await service_with_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    assert second_result.summary.cached is True
    # cache_age_seconds = cache_ttl - ttl = 300 - 250 = 50
    assert second_result.summary.cache_age_seconds == 50


# ── Test 2: Service handles empty response gracefully ─────────────────────────


@pytest.mark.asyncio
async def test_service_handles_empty_response_gracefully(
    service_no_redis, httpx_mock
):
    """Empty data from API → empty UsageResponse, no crash."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )

    # DB returns empty result set for ownership filter
    mock_result = MagicMock()
    mock_result.all.return_value = []
    service_no_redis._db_session.exec = AsyncMock(return_value=mock_result)

    result = await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    assert result is not None
    assert result.summary.total_invocations == 0
    assert result.summary.total_cost_usd == 0.0
    assert result.flows == []
    assert result.summary.active_flow_count == 0


# ── Test 3: Concurrent requests same user (no race conditions) ────────────────


@pytest.mark.asyncio
async def test_service_concurrent_requests_same_user(service_no_redis):
    """Multiple concurrent get_usage_summary calls for the same user complete successfully."""
    expected = _make_usage_response()

    async def call_service():
        with (
            patch.object(
                service_no_redis,
                "_fetch_from_langwatch",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                service_no_redis,
                "_filter_by_ownership",
                new=AsyncMock(return_value=([], {})),
            ),
            patch.object(
                service_no_redis,
                "_aggregate_with_metadata",
                return_value=expected,
            ),
        ):
            return await service_no_redis.get_usage_summary(
                params=SAMPLE_PARAMS,
                allowed_flow_ids={FLOW_UUID_A},
                api_key=API_KEY,
                org_id=ORG_ID,
            )

    results = await asyncio.gather(*[call_service() for _ in range(5)])

    assert len(results) == 5
    for result in results:
        assert result is not None
        assert result.summary.total_invocations == 2


# ── Test 4: Key lifecycle — save → validate → status → invalidate ────────────


@pytest.mark.asyncio
async def test_service_key_lifecycle(service_with_redis, redis_mock, httpx_mock):
    """Full key lifecycle: save, validate (200), check status, invalidate cache."""
    patch_target = "langflow.services.langwatch.service.get_settings_service"

    import base64
    import hashlib

    from cryptography.fernet import Fernet

    test_secret = "integration-test-secret-key-xyz"  # noqa: S105
    key = base64.urlsafe_b64encode(hashlib.sha256(test_secret.encode()).digest())
    fernet = Fernet(key)
    test_api_key = "lw_lifecycle_key_abc123"

    mock_secret = MagicMock()
    mock_secret.get_secret_value.return_value = test_secret
    mock_auth = MagicMock()
    mock_auth.SECRET_KEY = mock_secret
    mock_settings_svc = MagicMock()
    mock_settings_svc.auth_settings = mock_auth

    stored = {}

    def capture_add(obj):
        stored["setting"] = obj

    service_with_redis._db_session.add = capture_add
    service_with_redis._db_session.commit = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])

    call_count = {"n": 0}

    async def mock_get_setting(_key: str):
        call_count["n"] += 1
        if call_count["n"] <= 1:
            return None
        return stored.get("setting")

    service_with_redis._get_setting = mock_get_setting

    # Step 1: Save the key
    with patch(patch_target, return_value=mock_settings_svc):
        await service_with_redis.save_key(test_api_key, ADMIN_UUID)

    assert "setting" in stored
    # Must be encrypted
    assert stored["setting"].value != test_api_key
    encrypted_val = stored["setting"].value
    decrypted = fernet.decrypt(encrypted_val.encode()).decode()
    assert decrypted == test_api_key

    # Step 2: Validate against LangWatch (returns 200)
    httpx_mock.add_response(
        method="GET",
        url=ANALYTICS_URL,
        status_code=200,
        json={"status": "ok"},
    )
    is_valid = await service_with_redis.validate_key(test_api_key)
    assert is_valid is True

    # Step 3: Check key status
    with patch(patch_target, return_value=mock_settings_svc):
        status = await service_with_redis.get_key_status()

    assert status.has_key is True
    assert status.key_preview is not None
    assert status.key_preview.startswith("****")

    # Step 4: Verify cache was invalidated on save
    redis_mock.keys.assert_called()


# ── Test 5: Ownership isolation — admin vs user ───────────────────────────────


@pytest.mark.asyncio
async def test_service_ownership_isolation_admin_vs_user(
    service_no_redis, httpx_mock
):
    """Admin sees all flows; regular user sees only their own flows."""
    # Two flows: Flow-A owned by USER_A, Flow-B owned by USER_B
    traces = [
        _make_trace("t1", "Alpha Bot", cost=0.005),
        _make_trace("t2", "Alpha Bot", cost=0.004),
        _make_trace("t3", "Beta Bot", cost=0.003),
    ]

    # Provide 2 pages worth of responses (one for admin, one for user)
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 3, "scrollId": None}},
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": traces, "pagination": {"totalHits": 3, "scrollId": None}},
    )

    # --- Admin path: allowed_flow_ids = empty set (means all flows) ---
    admin_row_a = MagicMock()
    admin_row_a.id = FLOW_UUID_A
    admin_row_a.name = "Alpha Bot"
    admin_row_a.user_id = USER_UUID_A
    admin_row_a.username = "alice"

    admin_row_b = MagicMock()
    admin_row_b.id = FLOW_UUID_B
    admin_row_b.name = "Beta Bot"
    admin_row_b.user_id = USER_UUID_B
    admin_row_b.username = "bob"

    admin_db_result = MagicMock()
    admin_db_result.all.return_value = [admin_row_a, admin_row_b]

    user_row_a = MagicMock()
    user_row_a.id = FLOW_UUID_A
    user_row_a.name = "Alpha Bot"
    user_row_a.user_id = USER_UUID_A
    user_row_a.username = "alice"

    user_db_result = MagicMock()
    user_db_result.all.return_value = [user_row_a]

    # Admin call: allowed_flow_ids has both flows
    service_no_redis._db_session.exec = AsyncMock(return_value=admin_db_result)
    admin_result = await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A, FLOW_UUID_B},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    admin_flow_names = {f.flow_name for f in admin_result.flows}
    assert "Alpha Bot" in admin_flow_names
    assert "Beta Bot" in admin_flow_names

    # User call: allowed_flow_ids has only their own flow
    service_no_redis._db_session.exec = AsyncMock(return_value=user_db_result)
    user_result = await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    user_flow_names = {f.flow_name for f in user_result.flows}
    assert "Alpha Bot" in user_flow_names
    assert "Beta Bot" not in user_flow_names


# ── Test 6: Large dataset pagination — 3+ pages ───────────────────────────────


@pytest.mark.asyncio
async def test_service_large_dataset_pagination(service_no_redis, httpx_mock):
    """Service correctly handles 3 pages of results from LangWatch."""
    page1_traces = [_make_trace(f"t{i}", "Paged Bot", cost=0.001) for i in range(3)]
    page2_traces = [_make_trace(f"t{i+3}", "Paged Bot", cost=0.001) for i in range(3)]
    page3_traces = [_make_trace(f"t{i+6}", "Paged Bot", cost=0.001) for i in range(2)]

    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": page1_traces,
            "pagination": {"totalHits": 8, "scrollId": "scroll-1"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": page2_traces,
            "pagination": {"totalHits": 8, "scrollId": "scroll-2"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": page3_traces,
            "pagination": {"totalHits": 8, "scrollId": None},
        },
    )

    flow_row = MagicMock()
    flow_row.id = FLOW_UUID_A
    flow_row.name = "Paged Bot"
    flow_row.user_id = USER_UUID_A
    flow_row.username = "alice"

    db_result = MagicMock()
    db_result.all.return_value = [flow_row]
    service_no_redis._db_session.exec = AsyncMock(return_value=db_result)

    result = await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    # 3 pages fetched
    requests = httpx_mock.get_requests()
    assert len(requests) == 3

    # All 8 traces combined → 1 flow with 8 invocations
    assert len(result.flows) == 1
    assert result.flows[0].flow_name == "Paged Bot"
    assert result.flows[0].invocation_count == 8
    assert result.summary.total_invocations == 8


# ── Test 7: All API calls include Authorization/X-Auth-Token header ───────────


@pytest.mark.asyncio
async def test_service_all_endpoints_authenticated(service_no_redis, httpx_mock):
    """All API calls to LangWatch include the expected auth header."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={"traces": [], "pagination": {"totalHits": 0, "scrollId": None}},
    )
    httpx_mock.add_response(
        method="GET",
        url=ANALYTICS_URL,
        status_code=200,
        json={"status": "ok"},
    )

    db_result = MagicMock()
    db_result.all.return_value = []
    service_no_redis._db_session.exec = AsyncMock(return_value=db_result)

    # Fetch traces — uses X-Auth-Token
    await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    # Validate key — uses Authorization: Bearer
    await service_no_redis.validate_key(API_KEY)

    all_requests = httpx_mock.get_requests()

    for req in all_requests:
        auth_header = req.headers.get("authorization") or req.headers.get("x-auth-token")
        assert auth_header is not None, (
            f"Request to {req.url} missing auth header. Headers: {dict(req.headers)}"
        )
        assert API_KEY in auth_header, (
            f"API key not in auth header for {req.url}: {auth_header!r}"
        )


# ── Test 8: HTTP 429/503 responses propagate as HTTPStatusError ───────────────


@pytest.mark.asyncio
async def test_service_429_rate_limit_propagates(service_no_redis, httpx_mock):
    """HTTP 429 (rate limited) raises httpx.HTTPStatusError — no silent retry."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=429,
        json={"error": "Too Many Requests"},
    )

    db_result = MagicMock()
    db_result.all.return_value = []
    service_no_redis._db_session.exec = AsyncMock(return_value=db_result)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await service_no_redis.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids={FLOW_UUID_A},
            api_key=API_KEY,
            org_id=ORG_ID,
        )

    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
async def test_service_503_unavailable_propagates(service_no_redis, httpx_mock):
    """HTTP 503 (service unavailable) raises httpx.HTTPStatusError."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        status_code=503,
        json={"error": "Service Unavailable"},
    )

    db_result = MagicMock()
    db_result.all.return_value = []
    service_no_redis._db_session.exec = AsyncMock(return_value=db_result)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await service_no_redis.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids={FLOW_UUID_A},
            api_key=API_KEY,
            org_id=ORG_ID,
        )

    assert exc_info.value.response.status_code == 503


# ── Test 9: Pagination scroll IDs pass correctly across 3 pages ───────────────


@pytest.mark.asyncio
async def test_service_pagination_scroll_ids_correct(service_no_redis, httpx_mock):
    """Verifies that scroll IDs from each page are forwarded to the next request."""
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t1", "Bot X")],
            "pagination": {"totalHits": 3, "scrollId": "scroll-page-2"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t2", "Bot X")],
            "pagination": {"totalHits": 3, "scrollId": "scroll-page-3"},
        },
    )
    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t3", "Bot X")],
            "pagination": {"totalHits": 3, "scrollId": None},
        },
    )

    db_result = MagicMock()
    db_result.all.return_value = []
    service_no_redis._db_session.exec = AsyncMock(return_value=db_result)

    await service_no_redis.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids={FLOW_UUID_A},
        api_key=API_KEY,
        org_id=ORG_ID,
    )

    all_requests = httpx_mock.get_requests()
    assert len(all_requests) == 3

    # Request 1: no scrollId
    body1 = json.loads(all_requests[0].content)
    assert "scrollId" not in body1 or body1.get("scrollId") is None

    # Request 2: scrollId from page 1
    body2 = json.loads(all_requests[1].content)
    assert body2.get("scrollId") == "scroll-page-2"

    # Request 3: scrollId from page 2
    body3 = json.loads(all_requests[2].content)
    assert body3.get("scrollId") == "scroll-page-3"


# ── Test 10: Flow runs ownership — non-admin blocked from another user's flow ─


@pytest.mark.asyncio
async def test_service_flow_runs_ownership_blocks_wrong_user(
    service_no_redis, httpx_mock
):
    """Non-admin requesting another user's flow runs gets empty result."""
    requesting_user = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    flow_owner = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    httpx_mock.add_response(
        method="POST",
        url=SEARCH_URL,
        json={
            "traces": [_make_trace("t1", "Other Bot", cost=0.01)],
            "pagination": {"totalHits": 1, "scrollId": None},
        },
    )

    # DB says the flow belongs to a DIFFERENT user
    mock_result = MagicMock()
    mock_result.all.return_value = [
        MagicMock(id=FLOW_UUID_C, name="Other Bot", user_id=flow_owner, username="eve")
    ]
    service_no_redis._db_session.exec = AsyncMock(return_value=mock_result)

    from langflow.services.langwatch.schemas import FlowRunsResponse

    response = await service_no_redis.fetch_flow_runs(
        flow_id=FLOW_UUID_C,
        flow_name="Other Bot",
        query=FlowRunsQueryParams(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            limit=10,
        ),
        api_key=API_KEY,
        requesting_user_id=requesting_user,
        is_admin=False,
    )

    # Non-admin blocked: empty result
    assert isinstance(response, FlowRunsResponse)
    assert response.runs == []
    assert response.total_runs_in_period == 0


# ── Test 11: Cache invalidation clears all usage:* keys ──────────────────────


@pytest.mark.asyncio
async def test_service_cache_invalidation_clears_all_usage_keys(
    service_with_redis, redis_mock
):
    """invalidate_cache() removes all keys matching usage:* pattern."""
    cache_keys = [
        b"usage:org1:flows:all:abc123",
        b"usage:org1:mcp:user:def456",
        b"usage:org2:flows:22222222:xyz789",
    ]
    redis_mock.keys = AsyncMock(return_value=cache_keys)
    redis_mock.delete = AsyncMock()

    await service_with_redis.invalidate_cache()

    redis_mock.keys.assert_called_once_with("usage:*")
    redis_mock.delete.assert_called_once_with(*cache_keys)
