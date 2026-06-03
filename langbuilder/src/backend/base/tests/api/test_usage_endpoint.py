"""F3-T3: Tests for GET /api/v1/usage/ endpoint.

Tests ownership logic, error responses, and happy path with mocked service.
Uses unittest.mock to avoid hitting external dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# ── Module loading helpers ────────────────────────────────────────────────────


def _stub_modules() -> None:
    stubs = [
        "fastapi_pagination",
        "langflow.api.utils",
        "langflow.api.utils.core",
        "lfx.services.deps",
        "openai",
    ]
    for mod in stubs:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()


def _load_router():
    _stub_modules()
    router_path = Path(__file__).parent.parent.parent / "langflow" / "api" / "v1" / "usage" / "router.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("langflow.api.v1.usage.router_module", router_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_user(*, is_superuser: bool = False, user_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_superuser = is_superuser
    return user


def _make_langwatch_service(usage_response=None, key="test-key-abc") -> AsyncMock:
    svc = AsyncMock()
    svc.get_stored_key.return_value = key
    svc.get_usage_summary.return_value = usage_response or _empty_usage_response()
    return svc


def _empty_usage_response():
    from langflow.services.langwatch.schemas import DateRange, UsageResponse, UsageSummary

    return UsageResponse(
        summary=UsageSummary(
            total_cost_usd=0.0,
            total_invocations=0,
            avg_cost_per_invocation_usd=0.0,
            active_flow_count=0,
            date_range=DateRange(),
        ),
        flows=[],
    )


# ── Tests: _get_flow_ids_for_user helper ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_flow_ids_for_user_with_user_id():
    """With user_id, only flows owned by that user are returned."""
    mod = _load_router()
    user_id = uuid4()
    expected_ids = {uuid4(), uuid4()}

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(fid,) for fid in expected_ids]
    mock_db.execute.return_value = mock_result

    result = await mod._get_flow_ids_for_user(mock_db, user_id)
    assert result == expected_ids
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_flow_ids_for_user_without_user_id():
    """Without user_id, all flows are returned."""
    mod = _load_router()
    all_ids = {uuid4(), uuid4(), uuid4()}

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(fid,) for fid in all_ids]
    mock_db.execute.return_value = mock_result

    result = await mod._get_flow_ids_for_user(mock_db, None)
    assert result == all_ids


# ── Tests: _get_stored_key_or_raise ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_stored_key_raises_503_when_no_key():
    """When no key is stored, raises 503 with KEY_NOT_CONFIGURED."""
    from fastapi import HTTPException

    mod = _load_router()
    langwatch = AsyncMock()
    langwatch.get_stored_key.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await mod._get_stored_key_or_raise(langwatch)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "KEY_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_get_stored_key_returns_key_when_configured():
    """When key is stored, returns the key."""
    mod = _load_router()
    langwatch = AsyncMock()
    langwatch.get_stored_key.return_value = "lw_live_abc123"

    result = await mod._get_stored_key_or_raise(langwatch)
    assert result == "lw_live_abc123"


# ── Tests: _raise_langwatch_http_error ───────────────────────────────────────


def test_raise_langwatch_key_not_configured_error():
    """LangWatchKeyNotConfiguredError maps to 503 KEY_NOT_CONFIGURED."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchKeyNotConfiguredError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchKeyNotConfiguredError("test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "KEY_NOT_CONFIGURED"
    assert exc_info.value.detail["retryable"] is False


def test_raise_langwatch_timeout_error():
    """LangWatchTimeoutError maps to 503 LANGWATCH_TIMEOUT."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchTimeoutError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchTimeoutError("test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_TIMEOUT"
    assert exc_info.value.detail["retryable"] is True


def test_raise_langwatch_unavailable_error():
    """LangWatchUnavailableError maps to 503 LANGWATCH_UNAVAILABLE."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchUnavailableError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchUnavailableError("test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_UNAVAILABLE"
    assert exc_info.value.detail["retryable"] is True


def test_raise_langwatch_connection_error():
    """LangWatchConnectionError maps to 503 LANGWATCH_UNAVAILABLE."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchConnectionError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchConnectionError("test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_UNAVAILABLE"


def test_raise_langwatch_invalid_key_error():
    """LangWatchInvalidKeyError maps to 422 INVALID_KEY."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchInvalidKeyError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchInvalidKeyError("test"))

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "INVALID_KEY"


def test_raise_langwatch_insufficient_credits_error():
    """LangWatchInsufficientCreditsError maps to 422 INSUFFICIENT_CREDITS."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchInsufficientCreditsError

    mod = _load_router()
    with pytest.raises(HTTPException) as exc_info:
        mod._raise_langwatch_http_error(LangWatchInsufficientCreditsError("test"))

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "INSUFFICIENT_CREDITS"


# ── Tests: get_usage_summary endpoint logic ───────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_effective_user_id_uses_own_id():
    """Non-admin: effective_user_id = current_user.id (ignores user_id param)."""
    mod = _load_router()
    user_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)
    langwatch = _make_langwatch_service()

    other_user_id = str(uuid4())

    # Mock DB to return empty set for user's flows
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    await mod.get_usage_summary(
        current_user=user,
        db=mock_db,
        langwatch=langwatch,
        user_id=other_user_id,  # Non-admin tries to pass another user's ID
    )

    # Verify DB was queried with current_user.id (not other_user_id)
    call_args = mock_db.execute.call_args
    # The WHERE clause should use the current user's ID
    stmt_str = str(call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
    # UUID comparison: compiled SQL may strip hyphens
    user_id_no_hyphens = str(user_id).replace("-", "")
    other_user_id_no_hyphens = str(other_user_id).replace("-", "")
    assert user_id_no_hyphens in stmt_str
    assert other_user_id_no_hyphens not in stmt_str


@pytest.mark.asyncio
async def test_admin_with_user_id_uses_specified_user_id():
    """Admin with user_id param: effective_user_id = params.user_id."""
    mod = _load_router()
    admin_id = uuid4()
    target_user_id = uuid4()
    admin_user = _make_user(is_superuser=True, user_id=admin_id)
    langwatch = _make_langwatch_service()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    await mod.get_usage_summary(
        current_user=admin_user,
        db=mock_db,
        langwatch=langwatch,
        user_id=str(target_user_id),
    )

    call_args = mock_db.execute.call_args
    stmt_str = str(call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
    target_user_id_no_hyphens = str(target_user_id).replace("-", "")
    assert target_user_id_no_hyphens in stmt_str


@pytest.mark.asyncio
async def test_admin_without_user_id_sees_all_flows():
    """Admin without user_id: all flows queried (no WHERE clause for user_id)."""
    mod = _load_router()
    admin_user = _make_user(is_superuser=True)
    langwatch = _make_langwatch_service()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    await mod.get_usage_summary(
        current_user=admin_user,
        db=mock_db,
        langwatch=langwatch,
    )

    # No user_id filter in DB query → the statement should NOT have a user_id WHERE
    call_args = mock_db.execute.call_args
    stmt_str = str(call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
    # When user_id is None, the query selects ALL flow IDs (no WHERE user_id =)
    assert "user_id" not in stmt_str.lower()


@pytest.mark.asyncio
async def test_usage_summary_happy_path_returns_response():
    """Happy path: returns UsageResponse from the service."""
    from langflow.services.langwatch.schemas import UsageResponse

    mod = _load_router()
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    result = await mod.get_usage_summary(current_user=user, db=mock_db, langwatch=langwatch)
    assert isinstance(result, UsageResponse)


@pytest.mark.asyncio
async def test_usage_summary_langwatch_timeout_returns_503():
    """LangWatchTimeoutError from service → 503 LANGWATCH_TIMEOUT."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchTimeoutError

    mod = _load_router()
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()
    langwatch.get_usage_summary.side_effect = LangWatchTimeoutError("timeout")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_usage_summary(current_user=user, db=mock_db, langwatch=langwatch)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_TIMEOUT"


@pytest.mark.asyncio
async def test_usage_summary_langwatch_unavailable_returns_503():
    """LangWatchUnavailableError from service → 503 LANGWATCH_UNAVAILABLE."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchUnavailableError

    mod = _load_router()
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service()
    langwatch.get_usage_summary.side_effect = LangWatchUnavailableError("down")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_usage_summary(current_user=user, db=mock_db, langwatch=langwatch)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_UNAVAILABLE"


@pytest.mark.asyncio
async def test_usage_summary_no_key_configured_returns_503():
    """When no key is configured, returns 503 KEY_NOT_CONFIGURED before calling service."""
    from fastapi import HTTPException

    mod = _load_router()
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch_service(key=None)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_usage_summary(current_user=user, db=mock_db, langwatch=langwatch)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "KEY_NOT_CONFIGURED"
    # Service should not be called if no key
    langwatch.get_usage_summary.assert_not_called()
