"""F3-T4: Tests for GET /api/v1/usage/{flow_id}/runs endpoint.

Tests ownership enforcement, error responses, and happy path with mocked service.

Note: Ownership is enforced by the router (DB lookup + 403), NOT by the service.
The service's fetch_flow_runs no longer accepts requesting_user_id or is_admin.
"""
from __future__ import annotations

import importlib.util
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
    spec = importlib.util.spec_from_file_location("langflow.api.v1.usage.router_t4", router_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_user(*, is_superuser: bool = False, user_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_superuser = is_superuser
    return user


def _make_langwatch(runs_response=None) -> AsyncMock:
    svc = AsyncMock()
    svc.get_stored_key.return_value = "lw_live_testkey"
    if runs_response is not None:
        svc.fetch_flow_runs.return_value = runs_response
    else:
        from langflow.services.langwatch.schemas import FlowRunsResponse
        svc.fetch_flow_runs.return_value = FlowRunsResponse(
            flow_id=uuid4(),
            flow_name="Test Flow",
            runs=[],
            total_runs_in_period=0,
        )
    return svc


def _make_db(flow_row=None, *, found: bool = True) -> AsyncMock:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    if found and flow_row:
        mock_result.fetchone.return_value = flow_row
    else:
        mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result
    return mock_db


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flow_runs_returns_404_when_flow_not_found():
    """Returns 404 FLOW_NOT_FOUND when flow does not exist in DB."""
    from fastapi import HTTPException

    mod = _load_router()
    user = _make_user(is_superuser=False)
    langwatch = _make_langwatch()
    db = _make_db(found=False)

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_flow_runs(
            flow_id=uuid4(),
            current_user=user,
            db=db,
            langwatch=langwatch,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "FLOW_NOT_FOUND"


@pytest.mark.asyncio
async def test_non_admin_cannot_access_another_users_flow():
    """Non-admin gets 403 FORBIDDEN when requesting another user's flow runs."""
    from fastapi import HTTPException

    mod = _load_router()
    requesting_user_id = uuid4()
    owner_user_id = uuid4()  # Different from requesting user

    user = _make_user(is_superuser=False, user_id=requesting_user_id)
    langwatch = _make_langwatch()
    flow_id = uuid4()
    db = _make_db(flow_row=(flow_id, "Some Flow", owner_user_id))

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_flow_runs(
            flow_id=flow_id,
            current_user=user,
            db=db,
            langwatch=langwatch,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_user_can_access_own_flow_runs():
    """User can access flow runs for a flow they own."""
    from langflow.services.langwatch.schemas import FlowRunsResponse

    mod = _load_router()
    user_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    db = _make_db(flow_row=(flow_id, "My Flow", user_id))  # Owner matches user

    result = await mod.get_flow_runs(
        flow_id=flow_id,
        current_user=user,
        db=db,
        langwatch=langwatch,
    )

    assert isinstance(result, FlowRunsResponse)
    langwatch.fetch_flow_runs.assert_called_once()


@pytest.mark.asyncio
async def test_admin_can_access_any_flow_runs():
    """Admin can access flow runs for any user's flow."""
    from langflow.services.langwatch.schemas import FlowRunsResponse

    mod = _load_router()
    admin_id = uuid4()
    other_user_id = uuid4()
    admin = _make_user(is_superuser=True, user_id=admin_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    db = _make_db(flow_row=(flow_id, "Other User's Flow", other_user_id))

    result = await mod.get_flow_runs(
        flow_id=flow_id,
        current_user=admin,
        db=db,
        langwatch=langwatch,
    )

    assert isinstance(result, FlowRunsResponse)
    langwatch.fetch_flow_runs.assert_called_once()


@pytest.mark.asyncio
async def test_flow_runs_no_key_configured_returns_503():
    """Returns 503 KEY_NOT_CONFIGURED when no API key is stored."""
    from fastapi import HTTPException

    mod = _load_router()
    user_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    langwatch.get_stored_key.return_value = None
    db = _make_db(flow_row=(flow_id, "My Flow", user_id))

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_flow_runs(
            flow_id=flow_id,
            current_user=user,
            db=db,
            langwatch=langwatch,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "KEY_NOT_CONFIGURED"
    langwatch.fetch_flow_runs.assert_not_called()


@pytest.mark.asyncio
async def test_flow_runs_service_unavailable_returns_503():
    """LangWatchUnavailableError from service → 503 LANGWATCH_UNAVAILABLE."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchUnavailableError

    mod = _load_router()
    user_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    langwatch.fetch_flow_runs.side_effect = LangWatchUnavailableError("down")
    db = _make_db(flow_row=(flow_id, "My Flow", user_id))

    with pytest.raises(HTTPException) as exc_info:
        await mod.get_flow_runs(
            flow_id=flow_id,
            current_user=user,
            db=db,
            langwatch=langwatch,
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_UNAVAILABLE"


@pytest.mark.asyncio
async def test_flow_runs_fetch_called_without_ownership_params():
    """fetch_flow_runs is called without requesting_user_id or is_admin params.

    Ownership is enforced by the router before calling the service.
    """
    mod = _load_router()
    admin_id = uuid4()
    other_user_id = uuid4()
    admin = _make_user(is_superuser=True, user_id=admin_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    db = _make_db(flow_row=(flow_id, "Test Flow", other_user_id))

    await mod.get_flow_runs(
        flow_id=flow_id,
        current_user=admin,
        db=db,
        langwatch=langwatch,
    )

    call_kwargs = langwatch.fetch_flow_runs.call_args[1]
    # These params should NOT be passed — ownership is handled by the router
    assert "is_admin" not in call_kwargs
    assert "requesting_user_id" not in call_kwargs
    # These params SHOULD be passed
    assert "flow_id" in call_kwargs
    assert "flow_name" in call_kwargs
    assert "query" in call_kwargs
    assert "api_key" in call_kwargs


@pytest.mark.asyncio
async def test_flow_runs_fetch_called_with_correct_flow_name():
    """fetch_flow_runs receives the flow_name from the DB lookup."""
    mod = _load_router()
    user_id = uuid4()
    user = _make_user(is_superuser=False, user_id=user_id)
    flow_id = uuid4()
    langwatch = _make_langwatch()
    db = _make_db(flow_row=(flow_id, "My Flow", user_id))

    await mod.get_flow_runs(
        flow_id=flow_id,
        current_user=user,
        db=db,
        langwatch=langwatch,
    )

    call_kwargs = langwatch.fetch_flow_runs.call_args[1]
    assert call_kwargs.get("flow_name") == "My Flow"
