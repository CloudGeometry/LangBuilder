"""Tests for F2-T2: httpx client configuration in LangWatchService.

Covers all acceptance criteria:
1. _create_httpx_client() returns httpx.AsyncClient
2. Default base URL contains langwatch.ai
3. Connect timeout = 5.0s
4. Read timeout = 30.0s
5. max_connections = 20, max_keepalive_connections = 10
6. Content-Type header is application/json
7. __init__ creates self._client as httpx.AsyncClient
8. aclose() method exists
"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock

import httpx

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_service():
    """Instantiate LangWatchService with a mock db_session."""
    from langflow.services.langwatch.service import LangWatchService

    return LangWatchService(db_session=AsyncMock())


# ── 1. _create_httpx_client() returns httpx.AsyncClient ──────────────────────


def test_create_httpx_client_returns_async_client():
    """_create_httpx_client() returns an httpx.AsyncClient instance."""
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert isinstance(client, httpx.AsyncClient)


# ── 2. Default base URL contains langwatch.ai ─────────────────────────────────


def test_create_httpx_client_default_base_url(monkeypatch):
    """Default base URL is https://app.langwatch.ai when no env var is set."""
    monkeypatch.delenv("LANGWATCH_ENDPOINT", raising=False)
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert "langwatch.ai" in str(client.base_url)


# ── 3. Connect timeout = 5.0s ────────────────────────────────────────────────


def test_create_httpx_client_connect_timeout():
    """Connect timeout is 5.0 seconds."""
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert client.timeout.connect == 5.0


# ── 4. Read timeout = 30.0s ──────────────────────────────────────────────────


def test_create_httpx_client_read_timeout():
    """Read timeout is 30.0 seconds."""
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert client.timeout.read == 30.0


# ── 5. Connection limits: max_connections=20, max_keepalive_connections=10 ────


def test_create_httpx_client_connection_limits():
    """Connection limits are max_connections=20, max_keepalive_connections=10.

    httpx 0.28+ does not expose .limits on AsyncClient directly; limits are
    stored on the underlying connection pool transport.
    """
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    # Access limits via the internal transport pool (httpx 0.28+)
    pool = client._transport._pool
    assert pool._max_connections == 20
    assert pool._max_keepalive_connections == 10


# ── 6. Content-Type header is application/json ───────────────────────────────


def test_create_httpx_client_content_type_header():
    """Default Content-Type header is application/json."""
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert client.headers.get("content-type") == "application/json"


# ── 7. __init__ creates self._client as httpx.AsyncClient ────────────────────


def test_service_init_creates_client():
    """LangWatchService.__init__ stores an httpx.AsyncClient as self._client."""
    svc = _make_service()
    assert hasattr(svc, "_client"), "LangWatchService must have a _client attribute"
    assert isinstance(svc._client, httpx.AsyncClient)


# ── 8. aclose() method exists ────────────────────────────────────────────────


def test_aclose_method_exists():
    """LangWatchService has an aclose() async method."""
    from langflow.services.langwatch.service import LangWatchService

    assert hasattr(LangWatchService, "aclose"), (
        "LangWatchService must have an aclose() method"
    )
    assert inspect.iscoroutinefunction(LangWatchService.aclose), (
        "aclose() must be an async method"
    )


# ── 9. Custom endpoint via env var ────────────────────────────────────────────


def test_create_httpx_client_custom_endpoint(monkeypatch):
    """Respects LANGWATCH_ENDPOINT env var override."""
    monkeypatch.setenv("LANGWATCH_ENDPOINT", "https://custom.langwatch.example.com")
    from langflow.services.langwatch.service import LangWatchService

    client = LangWatchService._create_httpx_client()
    assert "custom.langwatch.example.com" in str(client.base_url)
