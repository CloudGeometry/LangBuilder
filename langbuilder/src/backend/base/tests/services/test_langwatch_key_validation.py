"""Tests for F2-T8: validate_key() method in LangWatchService.

Covers:
1. validate_key() returns True for 200 response
2. validate_key() returns False for 401
3. validate_key() returns False for 403
4. validate_key() raises LangWatchConnectionError on network error
5. validate_key() raises ValueError for empty string
6. validate_key() makes request to analytics/usage endpoint
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from langflow.services.langwatch.exceptions import LangWatchConnectionError
from langflow.services.langwatch.service import LangWatchService

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_API_KEY = "lw_test_valid_key_abc123"
_PATCH_TARGET = "langflow.services.langwatch.service.get_settings_service"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_service() -> LangWatchService:
    """Create a LangWatchService instance with mocked DB session and httpx client."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = MagicMock(spec=httpx.AsyncClient)
    svc.redis = None
    return svc


def _make_response(status_code: int) -> httpx.Response:
    """Create a minimal httpx.Response with the given status code."""
    return httpx.Response(status_code=status_code, content=b"{}")


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_key_returns_true_for_valid_key():
    """200 response from LangWatch → validate_key() returns True."""
    svc = _make_service()
    svc._client.get = AsyncMock(return_value=_make_response(200))

    result = await svc.validate_key(VALID_API_KEY)

    assert result is True


@pytest.mark.asyncio
async def test_validate_key_returns_false_for_401():
    """401 response from LangWatch → validate_key() returns False (invalid key)."""
    svc = _make_service()
    svc._client.get = AsyncMock(return_value=_make_response(401))

    result = await svc.validate_key(VALID_API_KEY)

    assert result is False


@pytest.mark.asyncio
async def test_validate_key_returns_false_for_403():
    """403 response from LangWatch → validate_key() returns False."""
    svc = _make_service()
    svc._client.get = AsyncMock(return_value=_make_response(403))

    result = await svc.validate_key(VALID_API_KEY)

    assert result is False


@pytest.mark.asyncio
async def test_validate_key_raises_on_connection_error():
    """Network connection error → validate_key() raises LangWatchConnectionError."""
    svc = _make_service()
    svc._client.get = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with pytest.raises(LangWatchConnectionError):
        await svc.validate_key(VALID_API_KEY)


@pytest.mark.asyncio
async def test_validate_key_raises_on_timeout():
    """Timeout error → validate_key() raises LangWatchConnectionError."""
    svc = _make_service()
    svc._client.get = AsyncMock(
        side_effect=httpx.TimeoutException("Request timed out")
    )

    with pytest.raises(LangWatchConnectionError):
        await svc.validate_key(VALID_API_KEY)


@pytest.mark.asyncio
async def test_validate_key_with_empty_string_raises():
    """Empty string api_key → validate_key() raises ValueError."""
    svc = _make_service()

    with pytest.raises(ValueError, match="api_key"):
        await svc.validate_key("")


@pytest.mark.asyncio
async def test_validate_key_with_whitespace_only_raises():
    """Whitespace-only api_key → validate_key() raises ValueError."""
    svc = _make_service()

    with pytest.raises(ValueError, match="api_key"):
        await svc.validate_key("   ")


@pytest.mark.asyncio
async def test_validate_key_makes_request_to_analytics_endpoint():
    """validate_key() calls the analytics/usage endpoint with proper auth header."""
    svc = _make_service()
    svc._client.get = AsyncMock(return_value=_make_response(200))

    await svc.validate_key(VALID_API_KEY)

    svc._client.get.assert_called_once()
    call_args = svc._client.get.call_args

    # Verify the endpoint URL contains 'analytics' or 'usage'
    url_arg = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
    assert any(
        segment in url_arg for segment in ("analytics", "usage", "api")
    ), f"Expected analytics/usage endpoint, got: {url_arg!r}"

    # Verify Authorization header is set with the api_key
    headers_kwarg = call_args.kwargs.get("headers", {})
    assert VALID_API_KEY in str(headers_kwarg), (
        f"Expected api_key in headers, got: {headers_kwarg!r}"
    )


@pytest.mark.asyncio
async def test_validate_key_does_not_log_api_key(caplog):
    """validate_key() must never log the api_key value."""
    import logging

    svc = _make_service()
    svc._client.get = AsyncMock(return_value=_make_response(200))

    with caplog.at_level(logging.DEBUG, logger="langflow.services.langwatch.service"):
        await svc.validate_key(VALID_API_KEY)

    for record in caplog.records:
        assert VALID_API_KEY not in record.getMessage(), (
            f"API key found in log: {record.getMessage()!r}"
        )
