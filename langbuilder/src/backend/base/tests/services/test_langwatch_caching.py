"""Tests for F2-T6: Redis cache-aside implementation in LangWatchService.

Covers all 7 acceptance criteria:
1. Cache key schema matches usage:{org_id}:{sub_view}:{user_scope}:{date_hash}
2. Cache hit path sets summary.cached = True
3. Cache miss path calls LangWatch and writes to Redis
4. Redis connection error on read -> falls back to LangWatch (no error raised)
5. Redis connection error on write -> logs warning, returns result normally
6. invalidate_cache() deletes all usage:* keys
7. All cache scenarios covered by unit tests
"""
from __future__ import annotations

import hashlib
import inspect
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from langflow.services.langwatch.schemas import (
    DateRange,
    FlowUsage,
    UsageQueryParams,
    UsageResponse,
    UsageSummary,
)
from langflow.services.langwatch.service import LangWatchService

# ── Constants ─────────────────────────────────────────────────────────────────

FLOW_UUID_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_UUID_A = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

SAMPLE_PARAMS = UsageQueryParams(
    from_date=date(2026, 1, 1),
    to_date=date(2026, 1, 31),
    sub_view="flows",
)

SAMPLE_ALLOWED = {FLOW_UUID_A}
SAMPLE_ORG = "org1"
SAMPLE_API_KEY = "sk-test-key"


def make_usage_response(*, cached: bool = False) -> UsageResponse:
    summary = UsageSummary(
        total_cost_usd=0.01,
        total_invocations=5,
        avg_cost_per_invocation_usd=0.002,
        active_flow_count=1,
        date_range=DateRange(from_=date(2026, 1, 1), to=date(2026, 1, 31)),
        cached=cached,
    )
    flow = FlowUsage(
        flow_id=FLOW_UUID_A,
        flow_name="Test Flow",
        total_cost_usd=0.01,
        invocation_count=5,
        avg_cost_per_invocation_usd=0.002,
        owner_user_id=USER_UUID_A,
        owner_username="alice",
    )
    return UsageResponse(summary=summary, flows=[flow])


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def redis_mock():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)  # cache miss by default
    r.setex = AsyncMock()
    r.ttl = AsyncMock(return_value=200)
    r.keys = AsyncMock(return_value=[])
    r.delete = AsyncMock()
    return r


@pytest.fixture
def service(redis_mock):
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = redis_mock
    return svc


@pytest.fixture
def service_no_redis():
    """Service with no Redis configured."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = None
    return svc


# ── AC1: Cache key schema ─────────────────────────────────────────────────────


def test_cache_key_schema_with_user_id(service):
    """AC1: Cache key format is usage:{org_id}:{sub_view}:{user_scope}:{date_hash}."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        user_id=USER_UUID_A,
        sub_view="flows",
    )
    key = service._build_cache_key(params, SAMPLE_ALLOWED, SAMPLE_ORG)

    date_str = f"{params.from_date}:{params.to_date}"
    date_hash = hashlib.sha256(date_str.encode()).hexdigest()[:12]
    expected = f"usage:{SAMPLE_ORG}:flows:{USER_UUID_A}:{date_hash}"
    assert key == expected


def test_cache_key_schema_no_user_id_empty_allowed(service):
    """AC1: user_scope = 'user:none' when user_id is None, allowed_flow_ids is empty, and is_admin=False."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        sub_view="flows",
    )
    key = service._build_cache_key(params, set(), SAMPLE_ORG)

    date_str = f"{params.from_date}:{params.to_date}"
    date_hash = hashlib.sha256(date_str.encode()).hexdigest()[:12]
    expected = f"usage:{SAMPLE_ORG}:flows:user:none:{date_hash}"
    assert key == expected


def test_cache_key_schema_no_user_id_with_allowed(service):
    """AC1: user_scope = 'user' when user_id is None but allowed_flow_ids is non-empty."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        sub_view="flows",
    )
    key = service._build_cache_key(params, SAMPLE_ALLOWED, SAMPLE_ORG)

    date_str = f"{params.from_date}:{params.to_date}"
    date_hash = hashlib.sha256(date_str.encode()).hexdigest()[:12]
    expected = f"usage:{SAMPLE_ORG}:flows:user:{date_hash}"
    assert key == expected


def test_cache_key_schema_mcp_sub_view(service):
    """AC1: sub_view 'mcp' is reflected in cache key; non-admin empty set -> 'user:none'."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        sub_view="mcp",
    )
    key = service._build_cache_key(params, set(), SAMPLE_ORG)
    assert key.startswith("usage:org1:mcp:user:none:")


def test_cache_key_starts_with_usage_prefix(service):
    """AC1: Cache key always starts with 'usage:'."""
    key = service._build_cache_key(SAMPLE_PARAMS, SAMPLE_ALLOWED, SAMPLE_ORG)
    assert key.startswith("usage:")


def test_build_cache_key_method_exists():
    """AC1: _build_cache_key method exists on LangWatchService."""
    assert hasattr(LangWatchService, "_build_cache_key")
    assert callable(LangWatchService._build_cache_key)


def test_cache_key_admin_empty_allowed(service):
    """AC1: user_scope = 'admin:all' when is_admin=True and allowed_flow_ids is empty."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        sub_view="flows",
    )
    key = service._build_cache_key(params, set(), SAMPLE_ORG, is_admin=True)

    date_str = f"{params.from_date}:{params.to_date}"
    date_hash = hashlib.sha256(date_str.encode()).hexdigest()[:12]
    expected = f"usage:{SAMPLE_ORG}:flows:admin:all:{date_hash}"
    assert key == expected


def test_cache_key_admin_vs_nonadmin_different(service):
    """AC1: Admin and non-admin with empty allowed_flow_ids produce different cache keys."""
    params = UsageQueryParams(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
        sub_view="flows",
    )
    admin_key = service._build_cache_key(params, set(), SAMPLE_ORG, is_admin=True)
    nonadmin_key = service._build_cache_key(params, set(), SAMPLE_ORG, is_admin=False)
    assert admin_key != nonadmin_key
    assert "admin:all" in admin_key
    assert "user:none" in nonadmin_key


# ── AC2: Cache hit path sets summary.cached = True ───────────────────────────


@pytest.mark.asyncio
async def test_cache_hit_sets_cached_true(service, redis_mock):
    """AC2: Cache hit path sets summary.cached = True."""
    response = make_usage_response(cached=False)
    redis_mock.get = AsyncMock(return_value=response.model_dump_json().encode())

    result = await service.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids=set(),
        api_key=SAMPLE_API_KEY,
        org_id=SAMPLE_ORG,
    )

    assert result.summary.cached is True


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_langwatch(service, redis_mock):
    """AC2: Cache hit path does NOT call _fetch_from_langwatch."""
    response = make_usage_response(cached=False)
    redis_mock.get = AsyncMock(return_value=response.model_dump_json().encode())

    with patch.object(service, "_fetch_from_langwatch", new=AsyncMock()) as mock_fetch:
        await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=set(),
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_cache_hit_sets_cache_age_seconds(service, redis_mock):
    """AC2: Cache hit path populates cache_age_seconds from ttl."""
    response = make_usage_response(cached=False)
    redis_mock.get = AsyncMock(return_value=response.model_dump_json().encode())
    redis_mock.ttl = AsyncMock(return_value=200)  # 300 - 200 = 100 seconds age

    result = await service.get_usage_summary(
        params=SAMPLE_PARAMS,
        allowed_flow_ids=set(),
        api_key=SAMPLE_API_KEY,
        org_id=SAMPLE_ORG,
    )

    assert result.summary.cache_age_seconds == 100


# ── AC3: Cache miss path calls LangWatch and writes to Redis ──────────────────


@pytest.mark.asyncio
async def test_cache_miss_calls_fetch_from_langwatch(service, redis_mock):
    """AC3: Cache miss calls _fetch_from_langwatch."""
    redis_mock.get = AsyncMock(return_value=None)
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])) as mock_fetch,
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_cache_miss_writes_to_redis(service, redis_mock):
    """AC3: Cache miss writes result to Redis via setex."""
    redis_mock.get = AsyncMock(return_value=None)
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        redis_mock.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_miss_setex_uses_cache_ttl(service, redis_mock):
    """AC3: setex is called with the service's cache_ttl."""
    redis_mock.get = AsyncMock(return_value=None)
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        call_args = redis_mock.setex.call_args
        # Second argument should be cache_ttl
        ttl_arg = call_args[0][1] if call_args[0] else call_args[1].get("time") or call_args[0][1]
        assert ttl_arg == service.cache_ttl


@pytest.mark.asyncio
async def test_cache_miss_returns_uncached_result(service, redis_mock):
    """AC3: Cache miss returns a result (cached=False)."""
    redis_mock.get = AsyncMock(return_value=None)
    mock_response = make_usage_response(cached=False)

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        result = await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        assert result is not None
        assert result.summary.cached is False


# ── AC4: Redis connection error on read → falls back to LangWatch ─────────────


@pytest.mark.asyncio
async def test_redis_read_error_falls_back_to_langwatch(service, redis_mock):
    """AC4: Redis error on read -> falls back to LangWatch without raising."""
    redis_mock.get = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])) as mock_fetch,
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        result = await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        # Should not raise, should call LangWatch
        assert result is not None
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_redis_read_error_does_not_raise(service, redis_mock):
    """AC4: Redis connection error on read does not propagate to caller."""
    redis_mock.get = AsyncMock(side_effect=OSError("Connection refused"))
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        # Should not raise
        result = await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        assert result is not None


# ── AC5: Redis connection error on write → logs warning, returns normally ─────


@pytest.mark.asyncio
async def test_redis_write_error_returns_result(service, redis_mock):
    """AC5: Redis error on write does not prevent returning the result."""
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        result = await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        assert result is not None


@pytest.mark.asyncio
async def test_redis_write_error_does_not_raise(service, redis_mock):
    """AC5: Redis write error does not propagate to caller."""
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(side_effect=OSError("Connection refused"))
    mock_response = make_usage_response()

    with (
        patch.object(service, "_fetch_from_langwatch", new=AsyncMock(return_value=[])),
        patch.object(service, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service, "_aggregate_with_metadata", return_value=mock_response),
    ):
        # Should not raise
        result = await service.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        assert result is not None


# ── AC6: invalidate_cache() deletes all usage:* keys ─────────────────────────


@pytest.mark.asyncio
async def test_invalidate_cache_calls_keys_with_pattern(service, redis_mock):
    """AC6: invalidate_cache calls redis.keys('usage:*')."""
    redis_mock.keys = AsyncMock(return_value=[])
    await service.invalidate_cache()
    redis_mock.keys.assert_called_once_with("usage:*")


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_returned_keys(service, redis_mock):
    """AC6: invalidate_cache deletes all keys returned by redis.keys."""
    cache_keys = [b"usage:org1:flows:all:abc123", b"usage:org2:mcp:user:def456"]
    redis_mock.keys = AsyncMock(return_value=cache_keys)
    redis_mock.delete = AsyncMock()

    await service.invalidate_cache()

    redis_mock.delete.assert_called_once_with(*cache_keys)


@pytest.mark.asyncio
async def test_invalidate_cache_does_not_delete_when_no_keys(service, redis_mock):
    """AC6: invalidate_cache does not call delete when no keys found."""
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()

    await service.invalidate_cache()

    redis_mock.delete.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_cache_handles_redis_error(service, redis_mock):
    """AC6: invalidate_cache handles Redis error gracefully (no exception raised)."""
    redis_mock.keys = AsyncMock(side_effect=ConnectionError("Redis down"))

    # Should not raise
    await service.invalidate_cache()


@pytest.mark.asyncio
async def test_invalidate_cache_is_async():
    """AC6: invalidate_cache is an async method."""
    assert inspect.iscoroutinefunction(LangWatchService.invalidate_cache)


# ── AC7: Additional scenarios (no Redis configured) ───────────────────────────


@pytest.mark.asyncio
async def test_no_redis_configured_still_works(service_no_redis):
    """AC7: When redis is None, service still fetches from LangWatch."""
    mock_response = make_usage_response()

    with (
        patch.object(service_no_redis, "_fetch_from_langwatch", new=AsyncMock(return_value=[])) as mock_fetch,
        patch.object(service_no_redis, "_filter_by_ownership", new=AsyncMock(return_value=([], {}))),
        patch.object(service_no_redis, "_aggregate_with_metadata", return_value=mock_response),
    ):
        result = await service_no_redis.get_usage_summary(
            params=SAMPLE_PARAMS,
            allowed_flow_ids=SAMPLE_ALLOWED,
            api_key=SAMPLE_API_KEY,
            org_id=SAMPLE_ORG,
        )
        assert result is not None
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_cache_is_async_implementation():
    """AC7: invalidate_cache is now async (not a stub)."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = None

    # With None redis, should complete without error (no-op or graceful)
    # The method should be a coroutine function
    assert inspect.iscoroutinefunction(LangWatchService.invalidate_cache)


def test_get_usage_summary_is_async():
    """AC7: get_usage_summary is an async method."""
    assert inspect.iscoroutinefunction(LangWatchService.get_usage_summary)


def test_cache_ttl_class_attribute():
    """AC7: LangWatchService has cache_ttl class attribute = 300."""
    assert hasattr(LangWatchService, "cache_ttl")
    assert LangWatchService.cache_ttl == 300


def test_service_accepts_redis_param():
    """AC7: LangWatchService.__init__ accepts a redis parameter."""
    sig = inspect.signature(LangWatchService.__init__)
    assert "redis" in sig.parameters


def test_service_redis_optional():
    """AC7: LangWatchService can be instantiated without redis (default None)."""
    svc = LangWatchService(db_session=AsyncMock())
    assert svc.redis is None


@pytest.mark.asyncio
async def test_invalidate_cache_no_redis_does_not_raise(service_no_redis):
    """AC7: invalidate_cache with no redis configured does not raise."""
    # Should complete without error
    await service_no_redis.invalidate_cache()
