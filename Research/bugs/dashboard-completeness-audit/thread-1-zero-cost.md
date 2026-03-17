---
skill: serious-research
slug: dashboard-completeness-audit
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
thread: 1
title: "Zero Cost Root Cause"
---

# Thread 1: Zero Cost Root Cause

## Summary

Token counts and cost are **always null** in LangWatch traces because the LangWatch SDK's LangChain callback handler (`on_llm_end`) only recognizes OpenAI's `token_usage` key format. It fails to capture tokens from Anthropic (which uses a different key/sub-key naming scheme) and from any streaming invocation (where token data lives on the AIMessage, not in `llm_output`).

## Root Cause

**Three compounding failures prevent token data from reaching the Usage dashboard:**

### Bug 1: Anthropic uses `"usage"` key, not `"token_usage"`

**File:** `.venv/lib/python3.12/site-packages/langwatch/langchain.py`, lines 285-292

```python
# LangWatch SDK on_llm_end (line 285-292):
if response.llm_output and "token_usage" in response.llm_output:
    usage = response.llm_output["token_usage"]
    span.update(
        metrics=SpanMetrics(
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
    )
```

Anthropic's `ChatAnthropic._format_output()` constructs `llm_output` by filtering `data_dict` to exclude `content`, `role`, `type` -- leaving:
```python
llm_output = {
    "id": "msg_...",
    "model": "claude-3-...",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 25, "output_tokens": 11},  # KEY: "usage", NOT "token_usage"
    "model_name": "claude-3-..."
}
```

**Mismatch:** The SDK checks for `"token_usage"` (OpenAI convention). Anthropic uses `"usage"` with sub-keys `"input_tokens"` / `"output_tokens"` instead of `"prompt_tokens"` / `"completion_tokens"`.

### Bug 2: Streaming path yields `llm_output = None`

**File:** `langchain_core/language_models/chat_models.py`, `_generate_with_cache()` and `generate_from_stream()`

When the Langflow Agent component calls `astream_events()` (see `src/lfx/src/lfx/base/agents/agent.py`, line 266), LangChain's `_generate_with_cache()` detects it should stream and calls:

```python
result = generate_from_stream(iter(chunks))
```

`generate_from_stream()` returns:
```python
return ChatResult(
    generations=[ChatGeneration(message=message_chunk_to_message(generation.message), ...)],
    # NOTE: No llm_output parameter -- defaults to None
)
```

So when `on_llm_end(flattened_output)` fires, `flattened_output.llm_output` is `None`. The LangWatch callback's guard `if response.llm_output` is **always False** for streaming.

**This is the primary path.** The Langflow Agent component always uses `astream_events()`, making this the dominant code path.

### Bug 3: Token data exists on `AIMessage.usage_metadata` but is never read

For both streaming and non-streaming Anthropic calls, LangChain sets:
```python
msg.usage_metadata = {"input_tokens": 25, "output_tokens": 11, "total_tokens": 36}
```

This data is available at:
```
response.generations[0][0].message.usage_metadata
```

But the LangWatch SDK's `on_llm_end` **never inspects** `response.generations[*][*].message.usage_metadata`.

## Evidence

### Live Trace Data (queried 2026-03-17)

```
trace 4c3b572d6a20c6e1a1ce2474ac1c2000:
  LLM span: type=llm, model=anthropic/claude-haiku-4-5-20251001
  span metrics: {}          <-- EMPTY, no tokens
  trace metrics:
    prompt_tokens: null
    completion_tokens: null
    total_cost: null
    tokens_estimated: false
```

All 4 traces in the past week show identical null metrics. LLM spans exist with correct model identification but empty metrics.

### Code Path Trace

| Step | File | Line | What Happens |
|------|------|------|-------------|
| 1 | `src/lfx/src/lfx/base/agents/agent.py` | 266 | Agent calls `runnable.astream_events(...)` |
| 2 | `langchain_core/.../chat_models.py` | `_generate_with_cache` | Detects streaming, calls `self._stream()` |
| 3 | `langchain_anthropic/chat_models.py` | `_stream` | Anthropic streams chunks with usage in final chunk |
| 4 | `langchain_core/.../chat_models.py` | `generate_from_stream` | Assembles `ChatResult` WITHOUT `llm_output` |
| 5 | `langchain_core/.../chat_models.py` | `generate()` L111 | Calls `manager.on_llm_end(flattened_output)` with `llm_output=None` |
| 6 | `.venv/.../langwatch/langchain.py` | 285 | `if response.llm_output and "token_usage" in response.llm_output:` -> **False** |
| 7 | `.venv/.../langwatch/langchain.py` | 284 | `span.update(output=output)` -- output is set, but **no metrics** |
| 8 | `.venv/.../langwatch/telemetry/span.py` | 431-436 | Metrics are serialized as OTEL attribute `langwatch.metrics` |
| 9 | LangWatch API | - | Receives span with empty metrics, trace aggregates to null tokens/cost |
| 10 | `src/.../langwatch/service.py` | 321 | `_parse_trace()` reads `metrics.prompt_tokens` -> null |

### Comparison: How OpenAI Would Work (reference)

OpenAI's `ChatOpenAI._generate()` returns:
```python
ChatResult(
    ...,
    llm_output={"token_usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}, "model_name": "gpt-4"}
)
```

Key is `"token_usage"` (matches the LangWatch check). Sub-keys are `"prompt_tokens"` / `"completion_tokens"` (match the LangWatch extraction). **But only for non-streaming.** Streaming OpenAI would have the same Bug 2.

## Proposed Fix

### Option A: Patch `on_llm_end` in LangWatch SDK (preferred, upstream)

Modify `.venv/lib/python3.12/site-packages/langwatch/langchain.py`, `on_llm_end()` method (line 250-293):

```python
def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> Any:
    span = self.spans.get(str(run_id))
    if span is None:
        return

    # ... existing output handling (lines 255-283) ...

    span.update(output=output)

    # --- FIX: Multi-strategy token extraction ---
    prompt_tokens = None
    completion_tokens = None

    # Strategy 1: OpenAI format (existing)
    if response.llm_output and "token_usage" in response.llm_output:
        usage = response.llm_output["token_usage"]
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

    # Strategy 2: Anthropic format (llm_output.usage.input_tokens)
    elif response.llm_output and "usage" in response.llm_output:
        usage = response.llm_output["usage"]
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")

    # Strategy 3: LangChain unified usage_metadata on AIMessage
    if prompt_tokens is None and completion_tokens is None:
        for generations in response.generations:
            for g in generations:
                if hasattr(g, "message") and hasattr(g.message, "usage_metadata"):
                    um = g.message.usage_metadata
                    if um:
                        prompt_tokens = um.get("input_tokens")
                        completion_tokens = um.get("output_tokens")
                        break
            if prompt_tokens is not None:
                break

    if prompt_tokens is not None or completion_tokens is not None:
        span.update(
            metrics=SpanMetrics(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

    span.__exit__(None, None, None)
```

**Pros:** Fixes at source, covers all providers, handles streaming.
**Cons:** Modifying vendored SDK code; would need to be maintained across upgrades. Better to submit upstream PR to langwatch/langwatch-python.

### Option B: Monkey-patch in LangWatchTracer (pragmatic, local)

Modify `src/backend/base/langflow/services/tracing/langwatch.py` to wrap the callback returned by `get_langchain_callback()` with a patched `on_llm_end`:

```python
def get_langchain_callback(self) -> BaseCallbackHandler | None:
    if self.trace is None:
        return None

    callback = self.trace.get_langchain_callback()
    if callback is None:
        return None

    # Monkey-patch on_llm_end to handle Anthropic + streaming token formats
    original_on_llm_end = callback.on_llm_end

    def patched_on_llm_end(response, *, run_id, **kwargs):
        # Extract tokens before calling original (which may miss them)
        span = callback.spans.get(str(run_id))
        if span is not None:
            prompt_tokens, completion_tokens = _extract_tokens(response)
            if prompt_tokens is not None or completion_tokens is not None:
                from langwatch.domain import SpanMetrics
                span.update(metrics=SpanMetrics(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                ))
        return original_on_llm_end(response, run_id=run_id, **kwargs)

    callback.on_llm_end = patched_on_llm_end
    return callback


def _extract_tokens(response):
    """Extract tokens from LLMResult using multiple strategies."""
    prompt_tokens = None
    completion_tokens = None

    # Strategy 1: OpenAI format
    if response.llm_output and "token_usage" in response.llm_output:
        usage = response.llm_output["token_usage"]
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

    # Strategy 2: Anthropic format
    elif response.llm_output and "usage" in response.llm_output:
        usage = response.llm_output["usage"]
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")

    # Strategy 3: usage_metadata on AIMessage (works for streaming)
    if prompt_tokens is None:
        for generations in response.generations:
            for g in generations:
                if hasattr(g, "message") and hasattr(g.message, "usage_metadata"):
                    um = g.message.usage_metadata
                    if um:
                        prompt_tokens = um.get("input_tokens")
                        completion_tokens = um.get("output_tokens")
                        break
            if prompt_tokens is not None:
                break

    return prompt_tokens, completion_tokens
```

**Pros:** No SDK changes needed, survives SDK upgrades, testable locally.
**Cons:** Fragile (depends on callback internals), monkey-patching is harder to maintain.

### Option C: Extract tokens in `LangWatchTracer.end_trace()` (alternative)

Instead of patching the callback, capture token data from the component outputs in `end_trace()`:

```python
def end_trace(self, trace_id, trace_name, outputs=None, error=None, logs=()):
    if not self._ready:
        return
    if self.spans.get(trace_id):
        # Check if any child span has token data from the callback
        # If not, try to extract from component outputs
        span = self.spans[trace_id]
        if span.metrics is None or (not span.metrics.get("prompt_tokens") and not span.metrics.get("completion_tokens")):
            tokens = self._extract_tokens_from_outputs(outputs)
            if tokens:
                span.update(metrics=tokens)
        span.end(output=self._convert_to_langwatch_types(outputs), error=error)
```

**Cons:** Component outputs don't always contain token metadata; this is unreliable.

## Recommendation

**Option B (monkey-patch in LangWatchTracer)** for an immediate fix, combined with filing an upstream issue/PR for the LangWatch Python SDK to implement Option A natively. The monkey-patch approach:

1. Fixes the problem immediately without modifying vendored packages
2. Handles both non-streaming Anthropic (`"usage"` key) and streaming (via `usage_metadata`)
3. Is scoped to the LangWatchTracer class, keeping the change isolated
4. Falls back gracefully -- if the original callback already captured tokens, the patch won't override

## Files Referenced

| File | Location | Role |
|------|----------|------|
| `langwatch.py` (tracer) | `src/backend/base/langflow/services/tracing/langwatch.py` | Langflow's LangWatch tracer integration |
| `langchain.py` (SDK) | `.venv/.../langwatch/langchain.py` L250-293 | LangWatch SDK's LangChain callback -- **the broken `on_llm_end`** |
| `span.py` (SDK) | `.venv/.../langwatch/telemetry/span.py` L431-436 | How metrics are serialized to OTEL attributes |
| `tracing.py` (SDK) | `.venv/.../langwatch/telemetry/tracing.py` L261-265 | `get_langchain_callback()` creates `LangChainTracer` |
| `service.py` (LangWatch svc) | `src/backend/base/langflow/services/langwatch/service.py` L287-344 | `_parse_trace()` reads `metrics.prompt_tokens` from API |
| `agent.py` | `src/lfx/src/lfx/base/agents/agent.py` L266 | Agent uses `astream_events()` (streaming path) |
| `service.py` (tracing svc) | `src/backend/base/langflow/services/tracing/service.py` L503-518 | `get_langchain_callbacks()` distributes callbacks to all tracers |
| `langsmith.py` | `src/backend/base/langflow/services/tracing/langsmith.py` L207-208 | Reference: LangSmith returns `None` for callback (doesn't use LangChain callback) |
| `attributes.py` (SDK) | `.venv/.../langwatch/attributes.py` L68 | `LangWatchMetrics = "langwatch.metrics"` OTEL attribute key |
| `domain.py` (SDK) | `.venv/.../langwatch/domain.py` | `SpanMetrics` TypedDict: `{prompt_tokens, completion_tokens, cost}` |
