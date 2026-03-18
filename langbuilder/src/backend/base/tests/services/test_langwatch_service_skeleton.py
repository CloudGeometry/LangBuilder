"""RED-phase tests for the LangWatchService skeleton (F1-T5).

These tests verify the public interface of LangWatchService before F2 fills in
the implementations.  Every method stub is expected to raise NotImplementedError.
"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest


# ── 1. Import checks ──────────────────────────────────────────────────────────


def test_langwatch_service_is_importable():
    from langflow.services.langwatch.service import LangWatchService  # noqa: F401


def test_get_langwatch_service_factory_is_importable():
    from langflow.services.langwatch.service import get_langwatch_service  # noqa: F401


# ── 2. Instantiation ─────────────────────────────────────────────────────────


def test_langwatch_service_instantiates_with_mock_session():
    from langflow.services.langwatch.service import LangWatchService

    mock_session = AsyncMock()
    service = LangWatchService(db_session=mock_session)
    assert isinstance(service, LangWatchService)


# ── 3. All public methods exist ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "method_name",
    [
        "get_usage_summary",
        "fetch_flow_runs",
        "save_key",
        "get_stored_key",
        "get_key_status",
        "validate_key",
        "invalidate_cache",
    ],
)
def test_public_method_exists(method_name: str):
    from langflow.services.langwatch.service import LangWatchService

    assert hasattr(LangWatchService, method_name), (
        f"LangWatchService is missing method: {method_name}"
    )
    assert callable(getattr(LangWatchService, method_name))


# ── 4. Stubs raise NotImplementedError ───────────────────────────────────────


@pytest.fixture()
def service():
    from langflow.services.langwatch.service import LangWatchService

    return LangWatchService(db_session=AsyncMock())


@pytest.mark.asyncio
async def test_get_usage_summary_is_implemented(service):
    """F2-T6: get_usage_summary is now a real async implementation (no longer a stub)."""
    from langflow.services.langwatch.schemas import UsageQueryParams

    query = UsageQueryParams()
    allowed: set[UUID] = {uuid4()}
    # The method is now async and real; it should be a coroutine function
    assert inspect.iscoroutinefunction(service.get_usage_summary)


@pytest.mark.asyncio
async def test_save_key_raises_not_implemented(service):
    with pytest.raises(NotImplementedError):
        result = service.save_key("sk-test-key", uuid4())
        if inspect.isawaitable(result):
            await result


@pytest.mark.asyncio
async def test_get_stored_key_raises_not_implemented(service):
    with pytest.raises(NotImplementedError):
        result = service.get_stored_key()
        if inspect.isawaitable(result):
            await result


@pytest.mark.asyncio
async def test_get_key_status_raises_not_implemented(service):
    with pytest.raises(NotImplementedError):
        result = service.get_key_status()
        if inspect.isawaitable(result):
            await result


@pytest.mark.asyncio
async def test_validate_key_raises_not_implemented(service):
    with pytest.raises(NotImplementedError):
        result = service.validate_key("sk-test-key")
        if inspect.isawaitable(result):
            await result


@pytest.mark.asyncio
async def test_invalidate_cache_is_implemented(service):
    """F2-T6: invalidate_cache is now a real async implementation (no longer a stub)."""
    # The method is now async and real; it should be a coroutine function
    assert inspect.iscoroutinefunction(service.invalidate_cache)
    # With no redis, it should complete without error
    await service.invalidate_cache()


# ── 5. DI factory signature ───────────────────────────────────────────────────


def test_get_langwatch_service_is_callable():
    from langflow.services.langwatch.service import get_langwatch_service

    assert callable(get_langwatch_service)


def test_get_langwatch_service_has_session_param():
    from langflow.services.langwatch.service import get_langwatch_service

    sig = inspect.signature(get_langwatch_service)
    assert "session" in sig.parameters, (
        "get_langwatch_service must accept a 'session' parameter"
    )
