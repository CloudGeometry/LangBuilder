---
skill: serious-plan
slug: fix-token-capture
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
---

# Plan 02: Fix Token Capture (Zero-Cost Bug)

**FRs:** FR-006, FR-014 | **Priority:** P0
**Scope:** Monkey-patch `get_langchain_callback()` in `langwatch.py` to extract tokens from 3 locations instead of 1.

**Root file:** `src/backend/base/langflow/services/tracing/langwatch.py` (211 lines)
**Reference:** `src/backend/base/langflow/services/tracing/native_callback.py` lines 252-313 (4-location fallback)

---

## Task 0 -- Smoke Test (Baseline)

**Intent:** Confirm tokens are missing in LangWatch traces before patching.

**Steps:**
1. Run any flow that calls an LLM (Anthropic or OpenAI)
2. Check LangWatch dashboard -> open the trace -> inspect LLM span metrics
3. Confirm `prompt_tokens: null`, `completion_tokens: null`, `total_cost: null`

**AC:**
- [ ] LLM span has `metrics: {}` or null token values

**Rollback:** N/A -- read-only

---

## Task 1 -- Monkey-Patch `get_langchain_callback()`

**Intent:** Wrap the SDK callback's `on_llm_end` with a fallback that extracts tokens from Anthropic and streaming formats. Call the original first; inject only if metrics are still empty (true fallback).

**File:** `src/backend/base/langflow/services/tracing/langwatch.py`

**Why monkey-patch:** The bug is in the vendored LangWatch SDK (`langwatch/langchain.py` line 285-292). Patching the SDK directly would break on upgrades. A local wrapper is isolated, testable, and survives `pip install --upgrade`.

**Changes to `get_langchain_callback()` method** (lines 206-210):

Replace the current method:
```python
def get_langchain_callback(self) -> BaseCallbackHandler | None:
    if self.trace is None:
        return None

    return self.trace.get_langchain_callback()
```

With:
```python
def get_langchain_callback(self) -> BaseCallbackHandler | None:
    if self.trace is None:
        return None

    callback = self.trace.get_langchain_callback()
    if callback is None:
        return None

    original_on_llm_end = callback.on_llm_end

    def _patched_on_llm_end(response, *, run_id, **kwargs):
        # Let the SDK handle it first
        result = original_on_llm_end(response, run_id=run_id, **kwargs)

        # Check if the SDK captured tokens -- if so, do nothing
        span = callback.spans.get(str(run_id))
        if span is None:
            return result

        metrics = getattr(span, "metrics", None)
        has_tokens = (
            metrics is not None
            and (getattr(metrics, "prompt_tokens", None) is not None
                 or getattr(metrics, "completion_tokens", None) is not None)
        )
        if has_tokens:
            return result

        # Fallback: extract tokens from multiple locations
        prompt_tokens, completion_tokens = _extract_tokens_from_response(response)
        if prompt_tokens is not None or completion_tokens is not None:
            try:
                from langwatch.domain import SpanMetrics
                span.update(metrics=SpanMetrics(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                ))
            except Exception:  # noqa: BLE001
                logger.debug("Failed to inject token metrics into LangWatch span")

        return result

    callback.on_llm_end = _patched_on_llm_end
    return callback
```

**Add module-level helper** (after the class, or as a `@staticmethod`):

```python
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
                        _get = usage_meta.get if isinstance(usage_meta, dict) else lambda k, d=None, u=usage_meta: getattr(u, k, d)
                        prompt_tokens = _get("input_tokens")
                        completion_tokens = _get("output_tokens")
                        if prompt_tokens is not None:
                            break
            if prompt_tokens is not None:
                break

    return prompt_tokens, completion_tokens
```

**Key design decisions:**
- Call original `on_llm_end` **first** (line: `result = original_on_llm_end(...)`) -- this is a true fallback, not a pre-empt
- Check `span.metrics` after original runs -- only inject if SDK missed tokens
- `except Exception` with `BLE001 noqa` matches the existing error-handling pattern in this file (line 56)
- The `_get` lambda handles both `dict` and dataclass-style `usage_metadata` (same pattern as `native_callback.py` line 270)

**Sync pair:** `_extract_tokens_from_response` must check the same 3 locations the LangWatch SDK checks (currently only 1). If the SDK is upgraded to handle more locations, the fallback gracefully no-ops because it checks `has_tokens` first.

**AC:**
- [ ] `get_langchain_callback()` returns a patched callback
- [ ] Original `on_llm_end` still fires (SDK behavior preserved)
- [ ] Anthropic non-streaming: tokens extracted from `llm_output["usage"]`
- [ ] Streaming (any provider): tokens extracted from `message.usage_metadata`
- [ ] If SDK already captured tokens, patch does NOT overwrite
- [ ] No import errors -- `SpanMetrics` import is deferred inside the function

**Rollback:** Revert `get_langchain_callback()` to its original 3-line form.

---

## Task 2 -- Verify (End-to-End)

**Intent:** Confirm token counts appear in LangWatch traces and cost propagates to the Usage dashboard.

**Steps:**
1. Run a flow with Anthropic model (the primary provider)
2. Check LangWatch dashboard -> open the trace -> inspect LLM span
3. Confirm `prompt_tokens` and `completion_tokens` are non-null integers
4. Confirm `total_cost` is calculated (non-null, non-zero)
5. Open `/usage` dashboard -> confirm summary card shows non-zero cost
6. Confirm per-flow breakdown shows non-zero cost (requires Plan 01 wiring)

**AC:**
- [ ] LLM span metrics show token counts (e.g., `prompt_tokens: 25, completion_tokens: 11`)
- [ ] Trace-level `total_cost` is non-null
- [ ] Usage dashboard summary card `total_cost_usd > 0`
- [ ] Per-flow cost column shows non-zero values
