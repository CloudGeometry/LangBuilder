"""Sub-span utilities for detailed component tracing.

This module provides utilities to create sub-spans within components,
allowing detailed tracking of API calls, MCP operations, and other
internal operations with their timing, inputs, and outputs.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from langbuilder.services.tracing.service import TracingService


@dataclass
class SpanData:
    """Data collected during a span's execution."""

    name: str
    span_type: str  # "api", "mcp", "db", "tool", "llm", "custom"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None

    @property
    def duration_ms(self) -> float | None:
        """Duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to a dictionary suitable for logging."""
        result = {
            "span_name": self.name,
            "span_type": self.span_type,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
        }

        if self.inputs:
            result["inputs"] = _truncate_values(self.inputs)

        if self.outputs:
            result["outputs"] = _truncate_values(self.outputs)

        if self.metadata:
            result["metadata"] = self.metadata

        if self.error:
            result["error"] = str(self.error)

        return result


def _truncate_values(data: dict[str, Any], max_length: int = 500) -> dict[str, Any]:
    """Truncate long string values for cleaner logs."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) > max_length:
            result[key] = value[:max_length] + f"... ({len(value)} chars)"
        elif isinstance(value, dict):
            result[key] = _truncate_values(value, max_length)
        elif isinstance(value, list) and len(value) > 10:
            result[key] = f"[{len(value)} items]"
        else:
            result[key] = value
    return result


class ComponentSpanTracker:
    """Tracks sub-spans within a component for detailed tracing.

    Usage in a component:

        from langbuilder.services.tracing.spans import ComponentSpanTracker

        class MyAPIComponent(Component):
            async def make_request(self):
                tracker = ComponentSpanTracker(self)

                # Track an API call
                async with tracker.span("fetch_users", span_type="api") as span:
                    span.set_input("url", "https://api.example.com/users")
                    span.set_input("method", "GET")

                    response = await self.client.get("/users")

                    span.set_output("status_code", response.status_code)
                    span.set_output("user_count", len(response.json()))
                    span.set_metadata("cache_hit", False)

                return response

        # Or use the convenience decorators:
        async with tracker.api_call("Jira API", url=url, method="POST") as span:
            result = await client.post(url, json=data)
            span.set_output("status", result.status_code)
    """

    def __init__(self, component):
        """Initialize the span tracker.

        Args:
            component: The component instance (must have _tracing_service attribute)
        """
        self.component = component
        self._spans: list[SpanData] = []

    @asynccontextmanager
    async def span(
        self,
        name: str,
        span_type: str = "custom",
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Create an async sub-span for tracking an operation.

        Args:
            name: Descriptive name for the operation (e.g., "Jira Search", "MCP Tool Call")
            span_type: Type of operation - "api", "mcp", "db", "tool", "llm", "custom"
            inputs: Initial input values to record
            metadata: Additional metadata (e.g., endpoint URL, tool name)

        Yields:
            SpanContext: Context object to add inputs/outputs during execution
        """
        span_data = SpanData(
            name=name,
            span_type=span_type,
            inputs=inputs or {},
            metadata=metadata or {},
        )
        context = SpanContext(span_data)

        try:
            yield context
        except Exception as e:
            span_data.error = e
            raise
        finally:
            span_data.end_time = time.time()
            self._spans.append(span_data)
            self._log_span(span_data)

    @contextmanager
    def span_sync(
        self,
        name: str,
        span_type: str = "custom",
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Create a sync sub-span for tracking an operation."""
        span_data = SpanData(
            name=name,
            span_type=span_type,
            inputs=inputs or {},
            metadata=metadata or {},
        )
        context = SpanContext(span_data)

        try:
            yield context
        except Exception as e:
            span_data.error = e
            raise
        finally:
            span_data.end_time = time.time()
            self._spans.append(span_data)
            self._log_span(span_data)

    @asynccontextmanager
    async def api_call(
        self,
        name: str,
        url: str | None = None,
        method: str | None = None,
        **extra_inputs,
    ):
        """Convenience method for tracking API calls.

        Args:
            name: Name of the API (e.g., "Jira API", "Slack API")
            url: The API endpoint URL
            method: HTTP method (GET, POST, etc.)
            **extra_inputs: Additional inputs to record
        """
        inputs = {}
        if url:
            inputs["url"] = url
        if method:
            inputs["method"] = method
        inputs.update(extra_inputs)

        async with self.span(name, span_type="api", inputs=inputs) as span:
            yield span

    @asynccontextmanager
    async def mcp_call(
        self,
        tool_name: str,
        server: str | None = None,
        **tool_inputs,
    ):
        """Convenience method for tracking MCP tool calls.

        Args:
            tool_name: Name of the MCP tool being called
            server: MCP server name/identifier
            **tool_inputs: The inputs being passed to the tool
        """
        inputs = {"tool": tool_name}
        if server:
            inputs["server"] = server
        inputs["tool_inputs"] = tool_inputs

        async with self.span(f"MCP: {tool_name}", span_type="mcp", inputs=inputs) as span:
            yield span

    @asynccontextmanager
    async def llm_call(
        self,
        model: str,
        prompt_tokens: int | None = None,
        **extra_metadata,
    ):
        """Convenience method for tracking LLM calls.

        Args:
            model: The model name/identifier
            prompt_tokens: Number of input tokens (if known beforehand)
            **extra_metadata: Additional metadata
        """
        inputs = {"model": model}
        if prompt_tokens:
            inputs["prompt_tokens"] = prompt_tokens

        metadata = extra_metadata

        async with self.span(f"LLM: {model}", span_type="llm", inputs=inputs, metadata=metadata) as span:
            yield span

    def _log_span(self, span_data: SpanData) -> None:
        """Log the span data to the tracing service."""
        try:
            # Log to component's log method (shows in LangWatch)
            log_data = span_data.to_log_dict()

            # Format nicely for the trace
            if span_data.error:
                message = f"❌ {span_data.name} failed ({span_data.duration_ms:.0f}ms): {span_data.error}"
            else:
                message = f"✓ {span_data.name} ({span_data.duration_ms:.0f}ms)"

            # Add details
            details = []
            if span_data.inputs:
                details.append(f"Inputs: {span_data.inputs}")
            if span_data.outputs:
                details.append(f"Outputs: {_truncate_values(span_data.outputs)}")
            if span_data.metadata:
                details.append(f"Metadata: {span_data.metadata}")

            if details:
                message += "\n" + "\n".join(details)

            self.component.log(message, name=f"[{span_data.span_type.upper()}] {span_data.name}")

        except Exception as e:
            logger.debug(f"Failed to log span: {e}")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all spans tracked."""
        return {
            "total_spans": len(self._spans),
            "total_duration_ms": sum(s.duration_ms or 0 for s in self._spans),
            "spans": [s.to_log_dict() for s in self._spans],
            "errors": [str(s.error) for s in self._spans if s.error],
        }


class SpanContext:
    """Context object for adding data to a span during execution."""

    def __init__(self, span_data: SpanData):
        self._span_data = span_data

    def set_input(self, key: str, value: Any) -> None:
        """Add or update an input value."""
        self._span_data.inputs[key] = value

    def set_output(self, key: str, value: Any) -> None:
        """Add or update an output value."""
        self._span_data.outputs[key] = value

    def set_metadata(self, key: str, value: Any) -> None:
        """Add or update metadata."""
        self._span_data.metadata[key] = value

    def set_error(self, error: Exception) -> None:
        """Record an error (usually done automatically on exception)."""
        self._span_data.error = error

    @property
    def duration_ms(self) -> float:
        """Current duration in milliseconds."""
        return (time.time() - self._span_data.start_time) * 1000
