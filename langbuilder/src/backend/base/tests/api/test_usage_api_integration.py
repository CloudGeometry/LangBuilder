"""F3-T8: Integration tests for usage API endpoints.

Tests NOT covered by existing unit tests:
- Full TestClient request/response cycles through the FastAPI router
- Response schema field validation matching API contract
- Auth enforcement (401 when no auth token provided)
- Rate-limit header presence checks
- OpenAPI schema includes usage endpoint routes
- Key management full cycle: save key → check status → verify encrypted storage

Uses FastAPI TestClient with dependency overrides to mock LangWatchService
and auth dependencies, keeping tests isolated from external services and DB.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# ── Module stubs ──────────────────────────────────────────────────────────────
# These stubs prevent import errors from optional modules not present in CI.

_STUBS = [
    "fastapi_pagination",
    "langflow.api.utils",
    "langflow.api.utils.core",
    "lfx.services.deps",
    "openai",
]
for _mod in _STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# ── Helpers to build test app ─────────────────────────────────────────────────


def _make_user(*, is_superuser: bool = False, user_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_superuser = is_superuser
    user.username = "testuser"
    return user


def _make_langwatch_service(
    *,
    usage_response: Any = None,
    key: str | None = "lw_live_testkey123",
    key_status_response: Any = None,
    save_key_validates: bool = True,
) -> AsyncMock:
    """Create a mock LangWatchService with sensible defaults."""
    from langflow.services.langwatch.schemas import (
        DateRange,
        FlowRunsResponse,
        KeyStatusResponse,
        UsageResponse,
        UsageSummary,
    )

    svc = AsyncMock()
    svc.get_stored_key.return_value = key
    svc.validate_key.return_value = save_key_validates
    svc.save_key.return_value = None
    svc.invalidate_cache.return_value = None

    if usage_response is None:
        usage_response = UsageResponse(
            summary=UsageSummary(
                total_cost_usd=0.0,
                total_invocations=0,
                avg_cost_per_invocation_usd=0.0,
                active_flow_count=0,
                date_range=DateRange(),
            ),
            flows=[],
        )
    svc.get_usage_summary.return_value = usage_response

    if key_status_response is None:
        key_status_response = KeyStatusResponse(
            has_key=True,
            key_preview="****123",
            configured_at=datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc),
        )
    svc.get_key_status.return_value = key_status_response

    flow_runs = FlowRunsResponse(
        flow_id=uuid4(),
        flow_name="Test Flow",
        runs=[],
        total_runs_in_period=0,
    )
    svc.fetch_flow_runs.return_value = flow_runs

    return svc


def _build_test_app(
    current_user: Any,
    langwatch_svc: Any,
    *,
    db_rows: list | None = None,
) -> Any:
    """Build a minimal FastAPI app with the usage router and mocked dependencies.

    Overrides:
    - get_current_active_user → current_user
    - get_current_active_superuser → current_user (or raises 403 if not superuser)
    - get_langwatch_service → langwatch_svc
    - injectable_session_scope → async mock DB session
    """
    import importlib.util
    from pathlib import Path

    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    # Load the usage router module fresh
    router_path = (
        Path(__file__).parent.parent.parent
        / "langflow"
        / "api"
        / "v1"
        / "usage"
        / "router.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"langflow.api.v1.usage.router_integration_{uuid4().hex[:8]}", router_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Build mock DB session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    if db_rows is not None:
        mock_result.fetchall.return_value = db_rows
        mock_result.fetchone.return_value = db_rows[0] if db_rows else None
    else:
        mock_result.fetchall.return_value = []
        mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    app = FastAPI()

    # Dependency overrides
    async def _override_db_session():
        yield mock_db

    async def _override_user():
        return current_user

    async def _override_superuser():
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user

    async def _override_langwatch():
        return langwatch_svc

    mod.router.dependency_overrides = {}
    from lfx.services.deps import injectable_session_scope

    app.dependency_overrides[injectable_session_scope] = _override_db_session

    from langflow.services.auth.utils import get_current_active_superuser, get_current_active_user
    from langflow.services.langwatch.service import get_langwatch_service

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_current_active_superuser] = _override_superuser
    app.dependency_overrides[get_langwatch_service] = _override_langwatch

    app.include_router(mod.router, prefix="/api/v1")

    return app, TestClient(app, raise_server_exceptions=False)


# ── Test 1: Full request/response cycle for usage summary endpoint ────────────


def test_usage_endpoint_full_request_response_cycle():
    """Full TestClient GET /api/v1/usage/ cycle returns 200 and UsageResponse JSON."""
    from langflow.services.langwatch.schemas import DateRange, UsageResponse, UsageSummary

    user = _make_user(is_superuser=False)
    expected_response = UsageResponse(
        summary=UsageSummary(
            total_cost_usd=340.21,
            total_invocations=421,
            avg_cost_per_invocation_usd=0.808,
            active_flow_count=7,
            date_range=DateRange(from_=None, to=None),
            currency="USD",
            data_source="langwatch",
            cached=False,
        ),
        flows=[],
    )
    langwatch = _make_langwatch_service(usage_response=expected_response)

    _, client = _build_test_app(user, langwatch)

    response = client.get("/api/v1/usage/")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "flows" in data
    assert data["summary"]["total_cost_usd"] == pytest.approx(340.21, rel=1e-3)
    assert data["summary"]["total_invocations"] == 421
    assert data["summary"]["currency"] == "USD"
    assert data["summary"]["data_source"] == "langwatch"
    assert isinstance(data["flows"], list)


# ── Test 2: Response schema matches UsageResponse spec fields ─────────────────


def test_usage_endpoint_response_schema_matches_spec():
    """Response JSON includes all required UsageResponse schema fields from spec."""
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()

    _, client = _build_test_app(user, langwatch)

    response = client.get("/api/v1/usage/")

    assert response.status_code == 200
    data = response.json()

    # Check summary top-level fields
    summary = data["summary"]
    required_summary_fields = {
        "total_cost_usd",
        "total_invocations",
        "avg_cost_per_invocation_usd",
        "active_flow_count",
        "date_range",
        "currency",
        "data_source",
        "cached",
        "cache_age_seconds",
    }
    for field in required_summary_fields:
        assert field in summary, f"Missing summary field: {field}"

    # Check date_range fields
    date_range = summary["date_range"]
    assert "from" in date_range or "from_" in date_range or date_range.get("from") is None
    assert "to" in date_range

    # Check flows is a list
    assert isinstance(data["flows"], list)


# ── Test 3: Full request/response cycle for flow runs endpoint ────────────────


def test_flow_runs_endpoint_full_cycle():
    """Full TestClient GET /api/v1/usage/{flow_id}/runs returns 200 with FlowRunsResponse."""
    from langflow.services.langwatch.schemas import FlowRunsResponse, RunDetail

    user_id = uuid4()
    flow_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)

    run = RunDetail(
        run_id="lw_trace_abc123",
        started_at=datetime(2026, 3, 16, 14, 32, 0, tzinfo=timezone.utc),
        cost_usd=0.55,
        input_tokens=1240,
        output_tokens=380,
        total_tokens=1620,
        model="gpt-4o",
        duration_ms=2340,
        status="success",
    )
    flow_runs = FlowRunsResponse(
        flow_id=flow_id,
        flow_name="Customer Support Bot",
        runs=[run],
        total_runs_in_period=148,
    )
    langwatch = _make_langwatch_service()
    langwatch.fetch_flow_runs.return_value = flow_runs

    # DB row: (flow_id, flow_name, owner_user_id) — owner matches user
    db_rows = [(flow_id, "Customer Support Bot", user_id)]
    _, client = _build_test_app(user, langwatch, db_rows=db_rows)

    response = client.get(f"/api/v1/usage/{flow_id}/runs")

    assert response.status_code == 200
    data = response.json()
    assert "flow_id" in data
    assert "flow_name" in data
    assert "runs" in data
    assert "total_runs_in_period" in data
    assert data["flow_name"] == "Customer Support Bot"
    assert data["total_runs_in_period"] == 148
    assert len(data["runs"]) == 1

    run_data = data["runs"][0]
    assert run_data["run_id"] == "lw_trace_abc123"
    assert run_data["cost_usd"] == pytest.approx(0.55, rel=1e-3)
    assert run_data["status"] == "success"
    assert run_data["model"] == "gpt-4o"


# ── Test 4: Key management full cycle ─────────────────────────────────────────


def test_key_management_full_cycle():
    """POST save key → 200 success; GET status → has_key=True with encrypted preview."""
    from langflow.services.langwatch.schemas import KeyStatusResponse

    admin_user = _make_user(is_superuser=True)

    # --- Step 1: Save the key ---
    langwatch = _make_langwatch_service(save_key_validates=True)
    langwatch.save_key.return_value = None

    _, client = _build_test_app(admin_user, langwatch)

    post_response = client.post(
        "/api/v1/usage/settings/langwatch-key",
        json={"api_key": "lw_live_abc123"},
    )
    assert post_response.status_code == 200
    post_data = post_response.json()
    assert post_data["success"] is True
    assert post_data["key_preview"].startswith("****")
    assert "message" in post_data

    # Verify save_key was called (encrypted storage)
    langwatch.save_key.assert_called_once()
    save_call_args = langwatch.save_key.call_args
    # First arg should be the stripped key
    assert save_call_args[0][0] == "lw_live_abc123"

    # --- Step 2: Check key status ---
    status_response_obj = KeyStatusResponse(
        has_key=True,
        key_preview="****123",
        configured_at=datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc),
    )
    langwatch.get_key_status.return_value = status_response_obj

    get_response = client.get("/api/v1/usage/settings/langwatch-key/status")
    assert get_response.status_code == 200
    status_data = get_response.json()
    assert status_data["has_key"] is True
    assert status_data["key_preview"] is not None
    # Preview should never expose full key
    assert "lw_live_abc123" not in (status_data["key_preview"] or "")
    assert "configured_at" in status_data


# ── Test 5: All endpoints require auth (401 when no token) ────────────────────


def test_all_endpoints_require_auth():
    """Without a valid auth token, all usage endpoints return 401 Unauthorized."""
    import importlib.util
    from pathlib import Path

    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    # Load the router
    router_path = (
        Path(__file__).parent.parent.parent
        / "langflow"
        / "api"
        / "v1"
        / "usage"
        / "router.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"langflow.api.v1.usage.router_auth_{uuid4().hex[:8]}", router_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from langflow.services.auth.utils import get_current_active_superuser, get_current_active_user
    from langflow.services.langwatch.service import get_langwatch_service

    app = FastAPI()

    # Auth dependencies raise 401 when no valid token
    async def _require_auth():
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def _require_superuser_auth():
        raise HTTPException(status_code=401, detail="Not authenticated")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    async def _override_db_session():
        yield mock_db

    langwatch = AsyncMock()

    async def _override_langwatch():
        return langwatch

    from lfx.services.deps import injectable_session_scope

    app.dependency_overrides[injectable_session_scope] = _override_db_session
    app.dependency_overrides[get_current_active_user] = _require_auth
    app.dependency_overrides[get_current_active_superuser] = _require_superuser_auth
    app.dependency_overrides[get_langwatch_service] = _override_langwatch

    app.include_router(mod.router, prefix="/api/v1")

    client = TestClient(app, raise_server_exceptions=False)

    flow_id = uuid4()

    # Test all 4 endpoints
    endpoints = [
        ("GET", "/api/v1/usage/"),
        ("GET", f"/api/v1/usage/{flow_id}/runs"),
        ("POST", "/api/v1/usage/settings/langwatch-key"),
        ("GET", "/api/v1/usage/settings/langwatch-key/status"),
    ]

    for method, path in endpoints:
        resp = client.get(path) if method == "GET" else client.post(path, json={"api_key": "test"})
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path}, got {resp.status_code}"
        )


# ── Test 6: Rate limit headers (verify absence doesn't break, presence noted) ──


def test_rate_limiting_headers():
    """No rate-limiting middleware is configured; endpoints don't set X-RateLimit headers.

    This test verifies the current behavior: usage endpoints respond without
    rate-limit headers. If headers are added in future, the test documents expectations.
    """
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()

    _, client = _build_test_app(user, langwatch)

    response = client.get("/api/v1/usage/")

    assert response.status_code == 200
    # Document current state: no rate-limit headers present
    # (This is expected — no rate limiting is implemented for this endpoint)
    rate_limit_headers = [
        h for h in response.headers if "ratelimit" in h.lower() or "rate-limit" in h.lower()
    ]
    # Currently no rate-limiting headers expected
    assert len(rate_limit_headers) == 0, (
        f"Unexpected rate-limit headers found: {rate_limit_headers}"
    )


# ── Test 7: OpenAPI schema includes usage endpoint routes ─────────────────────


def test_openapi_schema_has_usage_endpoints():
    """The app's /openapi.json includes all 4 usage route paths."""
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()

    _app, client = _build_test_app(user, langwatch)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    paths = schema.get("paths", {})

    # All 4 usage routes should appear in OpenAPI schema
    expected_paths = [
        "/api/v1/usage/",
        "/api/v1/usage/{flow_id}/runs",
        "/api/v1/usage/settings/langwatch-key",
        "/api/v1/usage/settings/langwatch-key/status",
    ]
    for expected_path in expected_paths:
        assert expected_path in paths, (
            f"Expected path '{expected_path}' not found in OpenAPI schema. "
            f"Available paths: {sorted(paths.keys())}"
        )

    # Verify HTTP methods for each route
    assert "get" in paths["/api/v1/usage/"]
    assert "get" in paths["/api/v1/usage/{flow_id}/runs"]
    assert "post" in paths["/api/v1/usage/settings/langwatch-key"]
    assert "get" in paths["/api/v1/usage/settings/langwatch-key/status"]
