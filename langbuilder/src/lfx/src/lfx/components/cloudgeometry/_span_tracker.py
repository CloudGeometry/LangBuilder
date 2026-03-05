"""
Compatibility shim: ComponentSpanTracker was removed in Langflow 1.7.3.
Provides a no-op implementation that preserves the full CG component interface.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any


class _SpanContext:
    """No-op context yielded by span_sync / span — accepts all set_* calls."""

    def set_input(self, key: str, value: Any) -> None:
        pass

    def set_output(self, key: str, value: Any) -> None:
        pass

    def set_metadata(self, key: str, value: Any) -> None:
        pass


class ComponentSpanTracker:
    """No-op span tracker — tracing is handled natively by Langflow 1.7.3."""

    def __init__(self, component: Any) -> None:
        pass

    def __enter__(self) -> "ComponentSpanTracker":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def log(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_attribute(self, *args: Any, **kwargs: Any) -> None:
        pass

    @contextmanager
    def span_sync(
        self,
        name: str,
        span_type: str = "custom",
        inputs: dict | None = None,
        metadata: dict | None = None,
    ):
        """No-op sync span context manager."""
        yield _SpanContext()

    async def span(
        self,
        name: str,
        span_type: str = "custom",
        inputs: dict | None = None,
        metadata: dict | None = None,
    ):
        """No-op async span — returns a context that yields a SpanContext."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _noop():
            yield _SpanContext()

        return _noop()

    @contextmanager
    def api_call(self, name: str, url: str | None = None, method: str | None = None, **kwargs):
        """No-op API call span context manager."""
        yield _SpanContext()
