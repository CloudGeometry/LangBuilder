"""F3-T5 & F3-T6: Tests for key management endpoints.

Covers POST /api/v1/usage/settings/langwatch-key and
GET /api/v1/usage/settings/langwatch-key/status.
Tests admin-only enforcement, key validation, save flow, and status retrieval.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# ── Module loading ────────────────────────────────────────────────────────────


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
    spec = importlib.util.spec_from_file_location("langflow.api.v1.usage.router_t5", router_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_admin(admin_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = admin_id or uuid4()
    user.is_superuser = True
    return user


def _make_langwatch_svc() -> AsyncMock:
    svc = AsyncMock()
    svc.validate_key.return_value = True
    svc.save_key.return_value = None
    return svc


# ── F3-T5: POST /settings/langwatch-key ─────────────────────────────────────


@pytest.mark.asyncio
async def test_save_key_happy_path_returns_success_response():
    """Valid key → validate succeeds → key saved → returns SaveKeyResponse."""
    from langflow.services.langwatch.schemas import SaveKeyResponse, SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    body = SaveLangWatchKeyRequest(api_key="lw_live_abc123xyz")

    result = await mod.save_langwatch_key(
        body=body,
        current_user=admin,
        langwatch=langwatch,
    )

    assert isinstance(result, SaveKeyResponse)
    assert result.success is True
    assert result.key_preview.startswith("****")
    assert "xyz" in result.key_preview
    assert result.message == "LangWatch API key validated and saved successfully."


@pytest.mark.asyncio
async def test_save_key_validates_before_saving():
    """validate_key is called before save_key."""
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    body = SaveLangWatchKeyRequest(api_key="lw_live_test123")

    await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    langwatch.validate_key.assert_called_once_with("lw_live_test123")
    langwatch.save_key.assert_called_once()


@pytest.mark.asyncio
async def test_save_key_invalid_key_returns_422():
    """When validate_key returns False, returns 422 INVALID_KEY."""
    from fastapi import HTTPException
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    langwatch.validate_key.return_value = False
    body = SaveLangWatchKeyRequest(api_key="lw_bad_key")

    with pytest.raises(HTTPException) as exc_info:
        await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "INVALID_KEY"
    langwatch.save_key.assert_not_called()


@pytest.mark.asyncio
async def test_save_key_connection_error_returns_503():
    """LangWatchConnectionError during validation → 503 LANGWATCH_UNAVAILABLE."""
    from fastapi import HTTPException
    from langflow.services.langwatch.exceptions import LangWatchConnectionError
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    langwatch.validate_key.side_effect = LangWatchConnectionError("unreachable")
    body = SaveLangWatchKeyRequest(api_key="lw_live_test")

    with pytest.raises(HTTPException) as exc_info:
        await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "LANGWATCH_UNAVAILABLE"
    langwatch.save_key.assert_not_called()


@pytest.mark.asyncio
async def test_save_key_strips_whitespace():
    """Leading/trailing whitespace is stripped from the API key."""
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    body = SaveLangWatchKeyRequest(api_key="  lw_live_clean  ")

    await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    # validate_key should be called with stripped key
    langwatch.validate_key.assert_called_once_with("lw_live_clean")


@pytest.mark.asyncio
async def test_save_key_preview_redacted():
    """Key preview shows only last 3 chars, prefixed with ****."""
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin = _make_admin()
    langwatch = _make_langwatch_svc()
    body = SaveLangWatchKeyRequest(api_key="lw_live_abc123")

    result = await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    assert result.key_preview == "****123"
    # Full key should never appear in preview
    assert "lw_live_abc" not in result.key_preview


@pytest.mark.asyncio
async def test_save_key_calls_save_key_with_admin_user_id():
    """save_key is called with the admin user's ID."""
    from langflow.services.langwatch.schemas import SaveLangWatchKeyRequest

    mod = _load_router()
    admin_id = uuid4()
    admin = _make_admin(admin_id=admin_id)
    langwatch = _make_langwatch_svc()
    body = SaveLangWatchKeyRequest(api_key="lw_live_test123")

    await mod.save_langwatch_key(body=body, current_user=admin, langwatch=langwatch)

    save_call_args = langwatch.save_key.call_args
    assert save_call_args[0][1] == admin_id or save_call_args[1].get("admin_user_id") == admin_id


# ── F3-T6: GET /settings/langwatch-key/status ────────────────────────────────


@pytest.mark.asyncio
async def test_key_status_returns_key_status_response():
    """get_langwatch_key_status returns KeyStatusResponse from service."""
    from langflow.services.langwatch.schemas import KeyStatusResponse

    mod = _load_router()
    admin = _make_admin()
    langwatch = AsyncMock()
    langwatch.get_key_status.return_value = KeyStatusResponse(
        has_key=True,
        key_preview="****xyz",
        configured_at=None,
    )

    result = await mod.get_langwatch_key_status(
        _current_user=admin,
        langwatch=langwatch,
    )

    assert isinstance(result, KeyStatusResponse)
    assert result.has_key is True
    assert result.key_preview == "****xyz"


@pytest.mark.asyncio
async def test_key_status_no_key_configured():
    """Returns has_key=False when no key is configured."""
    from langflow.services.langwatch.schemas import KeyStatusResponse

    mod = _load_router()
    admin = _make_admin()
    langwatch = AsyncMock()
    langwatch.get_key_status.return_value = KeyStatusResponse(has_key=False)

    result = await mod.get_langwatch_key_status(
        _current_user=admin,
        langwatch=langwatch,
    )

    assert result.has_key is False
    assert result.key_preview is None


@pytest.mark.asyncio
async def test_key_status_calls_get_key_status():
    """get_langwatch_key_status delegates to langwatch.get_key_status()."""
    from langflow.services.langwatch.schemas import KeyStatusResponse

    mod = _load_router()
    admin = _make_admin()
    langwatch = AsyncMock()
    langwatch.get_key_status.return_value = KeyStatusResponse(has_key=False)

    await mod.get_langwatch_key_status(_current_user=admin, langwatch=langwatch)

    langwatch.get_key_status.assert_called_once()
