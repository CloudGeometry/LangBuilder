from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any, cast

import nanoid
from lfx.log.logger import logger
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from typing_extensions import override

from langflow.schema.data import Data
from langflow.services.tracing.base import BaseTracer

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from langchain.callbacks.base import BaseCallbackHandler
    from langwatch.tracer import ContextSpan
    from lfx.graph.vertex.base import Vertex

    from langflow.services.tracing.schema import Log


class LangWatchTracer(BaseTracer):
    flow_id: str
    tracer_provider = None

    def __init__(self, trace_name: str, trace_type: str, project_name: str, trace_id: UUID):
        self.trace_name = trace_name
        self.trace_type = trace_type
        self.project_name = project_name
        self.trace_id = trace_id
        self.flow_id = trace_name.split(" - ")[-1]

        try:
            self._ready: bool = self.setup_langwatch()
            if not self._ready:
                return

            # Pass the dedicated tracer_provider here
            self.trace = self._client.trace(trace_id=str(self.trace_id), tracer_provider=self.tracer_provider)
            self.trace.__enter__()
            self.spans: dict[str, ContextSpan] = {}

            name_without_id = " - ".join(trace_name.split(" - ")[0:-1])
            name_without_id = project_name if name_without_id == "None" else name_without_id
            self.trace.root_span.update(
                # nanoid to make the span_id globally unique, which is required for LangWatch for now
                span_id=f"{self.flow_id}-{nanoid.generate(size=6)}",
                name=name_without_id,
                type="workflow",
            )
        except Exception:  # noqa: BLE001
            logger.debug("Error setting up LangWatch tracer")
            self._ready = False

    @property
    def ready(self):
        return self._ready

    def setup_langwatch(self) -> bool:
        if "LANGWATCH_API_KEY" not in os.environ:
            return False
        try:
            import langwatch
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            # Initialize the shared provider if it doesn't exist
            if self.tracer_provider is None:
                api_key = os.environ["LANGWATCH_API_KEY"]
                endpoint = os.environ.get("LANGWATCH_ENDPOINT", "https://app.langwatch.ai")

                resource = Resource.create(attributes={"service.name": "langflow"})
                exporter = OTLPSpanExporter(
                    endpoint=f"{endpoint}/api/otel/v1/traces", headers={"Authorization": f"Bearer {api_key}"}
                )
                provider = TracerProvider(resource=resource)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                LangWatchTracer.tracer_provider = provider

                # Initialize LangWatch client but skip OTEL setup to avoid touching the global provider
                # causing it to not receive traces from FastAPIInstrumentor
                langwatch.setup(
                    api_key=api_key,
                    endpoint_url=endpoint,
                    skip_open_telemetry_setup=True,
                )

            self._client = langwatch
        except ImportError as e:
            logger.exception(f"{e}")
            return False
        return True

    @override
    def add_trace(
        self,
        trace_id: str,
        trace_name: str,
        trace_type: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        vertex: Vertex | None = None,
    ) -> None:
        if not self._ready:
            return
        # If user is not using session_id, then it becomes the same as flow_id, but
        # we don't want to have an infinite thread with all the flow messages
        if "session_id" in inputs and inputs["session_id"] != self.flow_id:
            self.trace.update(metadata=(self.trace.metadata or {}) | {"thread_id": inputs["session_id"]})

        name_without_id = " (".join(trace_name.split(" (")[0:-1])

        previous_nodes = (
            [span for key, span in self.spans.items() for edge in vertex.incoming_edges if key == edge.source_id]
            if vertex and len(vertex.incoming_edges) > 0
            else []
        )

        span = self.trace.span(
            # Add a nanoid to make the span_id globally unique, which is required for LangWatch for now
            span_id=f"{trace_id}-{nanoid.generate(size=6)}",
            name=name_without_id,
            type="component",
            parent=(previous_nodes[-1] if len(previous_nodes) > 0 else self.trace.root_span),
            input=self._convert_to_langwatch_types(inputs),
        )
        self.trace.set_current_span(span)
        self.spans[trace_id] = span

    @override
    def end_trace(
        self,
        trace_id: str,
        trace_name: str,
        outputs: dict[str, Any] | None = None,
        error: Exception | None = None,
        logs: Sequence[Log | dict] = (),
    ) -> None:
        if not self._ready:
            return
        if self.spans.get(trace_id):
            self.spans[trace_id].end(output=self._convert_to_langwatch_types(outputs), error=error)

    def end(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._ready:
            return
        self.trace.root_span.end(
            input=self._convert_to_langwatch_types(inputs) if self.trace.root_span.input is None else None,
            output=self._convert_to_langwatch_types(outputs) if self.trace.root_span.output is None else None,
            error=error,
        )

        if metadata and "flow_name" in metadata:
            self.trace.update(metadata=(self.trace.metadata or {}) | {
                "labels": [f"Flow: {metadata['flow_name']}"],
                "flow_id": self.flow_id,  # Stable identifier — survives flow renames
            })

        from langwatch.state import get_api_key

        if self.trace.api_key or get_api_key():
            try:
                self.trace.__exit__(None, None, None)
            except ValueError:  # ignoring token was created in a different Context errors
                return

    def _convert_to_langwatch_types(self, io_dict: dict[str, Any] | None):
        from langwatch.utils import autoconvert_typed_values

        if io_dict is None:
            return None
        converted = {}
        for key, value in io_dict.items():
            converted[key] = self._convert_to_langwatch_type(value)
        return autoconvert_typed_values(converted)

    def _convert_to_langwatch_type(self, value):
        from langchain_core.messages import BaseMessage
        from langwatch.langchain import langchain_message_to_chat_message, langchain_messages_to_chat_messages
        from lfx.schema.message import Message

        if isinstance(value, dict):
            value = {key: self._convert_to_langwatch_type(val) for key, val in value.items()}
        elif isinstance(value, list):
            value = [self._convert_to_langwatch_type(v) for v in value]
        elif isinstance(value, Message):
            if "prompt" in value:
                prompt = value.load_lc_prompt()
                if len(prompt.input_variables) == 0 and all(isinstance(m, BaseMessage) for m in prompt.messages):
                    value = langchain_messages_to_chat_messages([cast("list[BaseMessage]", prompt.messages)])
                else:
                    value = cast("dict", value.load_lc_prompt())
            elif value.sender:
                value = langchain_message_to_chat_message(value.to_lc_message())
            else:
                value = cast("dict", value.to_lc_document())
        elif isinstance(value, Data):
            value = cast("dict", value.to_lc_document())
        return value

    def get_langchain_callback(self) -> BaseCallbackHandler | None:
        if self.trace is None:
            return None

        callback = self.trace.get_langchain_callback()
        if callback is None:
            return None

        original_on_llm_end = callback.on_llm_end

        def _patched_on_llm_end(response, *, run_id, **kwargs):
            # The SDK only checks llm_output["token_usage"] (OpenAI format).
            # Anthropic and streaming responses store tokens elsewhere.
            # We must inject BEFORE calling the original because it closes
            # the OTel span via span.__exit__(), after which attribute
            # updates are silently dropped.
            span = callback.spans.get(str(run_id))
            if span is not None:
                # Fix A: Normalize model name so LangWatch's pricing table can match it.
                # LangChain sends raw API model IDs (e.g. "anthropic/claude-haiku-4-5-20251001")
                # but LangWatch's pricing table uses simplified names ("anthropic/claude-haiku-4.5").
                if span.model:
                    normalized = _normalize_model_name(span.model)
                    if normalized != span.model:
                        span.update(model=normalized)

                # Fix B: Inject token metrics for Anthropic and streaming responses.
                prompt_tokens, completion_tokens = _extract_tokens_from_response(response)
                if prompt_tokens is not None or completion_tokens is not None:
                    # Check if the SDK will handle this itself (OpenAI token_usage path)
                    llm_output = getattr(response, "llm_output", None) or {}
                    sdk_will_handle = isinstance(llm_output, dict) and "token_usage" in llm_output
                    if not sdk_will_handle:
                        try:
                            from langwatch.domain import SpanMetrics

                            span.update(metrics=SpanMetrics(
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                            ))
                        except Exception:  # noqa: BLE001
                            logger.debug("Failed to inject token metrics into LangWatch span")

            # Let the SDK handle everything else (output capture, span closing)
            return original_on_llm_end(response, run_id=run_id, **kwargs)

        callback.on_llm_end = _patched_on_llm_end
        return callback


def _normalize_model_name(model: str) -> str:
    """Normalize model names to match LangWatch's pricing table format.

    LangChain sends raw API model IDs with date suffixes and dashes for versions
    (e.g. "anthropic/claude-haiku-4-5-20251001"), but LangWatch's pricing table
    uses simplified names with dots (e.g. "anthropic/claude-haiku-4.5").

    Strips the date suffix and converts version dashes to dots.
    """
    # Strip date suffix: -YYYYMMDD (8 digits at end)
    normalized = re.sub(r"-\d{8}$", "", model)
    # Convert version dashes to dots: X-Y -> X.Y (single digits only)
    normalized = re.sub(r"(\d)-(\d)", r"\1.\2", normalized)
    return normalized


def _extract_tokens_from_response(response) -> tuple[int | None, int | None]:
    """Extract token counts from LLMResult using 3 strategies.

    Mirrors the multi-location fallback in native_callback.py._extract_token_usage().
    """
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    llm_output = getattr(response, "llm_output", None) or {}

    # Strategy 1: OpenAI format -- llm_output["token_usage"]
    if isinstance(llm_output, dict) and "token_usage" in llm_output:
        usage = llm_output["token_usage"]
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")

    # Strategy 2: Anthropic format -- llm_output["usage"] with input_tokens/output_tokens
    if prompt_tokens is None and isinstance(llm_output, dict) and "usage" in llm_output:
        usage = llm_output["usage"]
        if isinstance(usage, dict):
            prompt_tokens = usage.get("input_tokens")
            completion_tokens = usage.get("output_tokens")

    # Strategy 3: LangChain unified usage_metadata on AIMessage (works for streaming)
    if prompt_tokens is None:
        for gen_list in getattr(response, "generations", []) or []:
            for gen in gen_list:
                message = getattr(gen, "message", None)
                if message is not None:
                    usage_meta = getattr(message, "usage_metadata", None)
                    if usage_meta:
                        _get = (
                            usage_meta.get
                            if isinstance(usage_meta, dict)
                            else lambda k, d=None, _u=usage_meta: getattr(_u, k, d)
                        )
                        prompt_tokens = _get("input_tokens")
                        completion_tokens = _get("output_tokens")
                        if prompt_tokens is not None:
                            break
            if prompt_tokens is not None:
                break

    return prompt_tokens, completion_tokens
