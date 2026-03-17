---
skill: serious-plan
slug: trace-flow-matching-gap
status: active
parent: Research/bugs/trace-flow-matching-gap
created: 2026-03-17
---

# Fix Trace-to-Flow Matching — Implementation Plan

## Executive Summary

The Usage dashboard shows zero data because the service expects flow names in `trace.metadata.labels` but the LangWatch API doesn't surface span-level metadata. Flow names ARE available in the root span's `name` field. This plan modifies 3 methods in `service.py` to extract flow names from spans as a fallback, filter to workflow-type traces only, and add diagnostic logging.

**Key outcomes:**
- Usage dashboard displays cost/invocation data for executed flows
- Component-level traces filtered out (prevents over-counting)
- Diagnostic logging for unmatched traces
- Backward-compatible: still reads labels first, falls back to spans

## Project Configuration

| Variable | Value |
|----------|-------|
| `{CODEBASE_ROOT}` | `/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/` |
| `{TARGET_FILE}` | `src/backend/base/langflow/services/langwatch/service.py` |
| `{EVIDENCE_ROOT}` | `Research/bugs/trace-flow-matching-gap/evidence/` |

## Master Checklist

| # | Task | Risk | Status |
|---|------|------|--------|
| 0 | Smoke test: call Usage API, confirm zero data | — | pending |
| 1 | Add `includeSpans` to `_fetch_all_pages` payload | L | pending |
| 2 | Add span-based flow name extraction to `_parse_trace` | M | pending |
| 3 | Add span-based fallback to `_filter_by_ownership` | M | pending |
| 4 | Filter to workflow-type traces in `_fetch_from_langwatch` | M | pending |
| 5 | Add diagnostic logging | L | pending |
| 6 | Verify: Usage dashboard shows data after running a flow | — | pending |

---

## Task 0: Smoke Test

**Intent:** Confirm the bug exists in the running app.
**Action:** Call `GET /api/v1/usage/` with auth token. Confirm response has `total_invocations: 0` and `flows: []` despite traces existing in LangWatch.

---

## Task 1: Add `includeSpans` to fetch payload

**Risk:** L — additive change, no existing behavior modified
**Intent:** Request span data alongside traces so flow names can be extracted.
**File:** `service.py` — `_fetch_all_pages` method (~line 184)
**Scope:** "Done" means the API request includes `includeSpans: true` and the response contains span data.

**Change:**
After `"pageSize": PAGE_SIZE,` (line 187), add:
```python
"includeSpans": True,
```

**Acceptance criteria:**
- [ ] `_fetch_all_pages` payload includes `"includeSpans": True`
- [ ] Raw traces returned by `_fetch_all_pages` contain a `"spans"` key with span data

**Impact analysis:** `_fetch_all_pages` is called by `_fetch_from_langwatch` (line ~263). Downstream: `_parse_trace` and `_filter_by_ownership` already access `trace.get("spans")` for model extraction (line 303). Adding span data makes this existing code work better.

**Rollback:** Remove the `"includeSpans": True` line.

**Note:** This increases API response payload size. Each trace may have 5-20 spans. For 100 traces, this is ~50KB additional data. Acceptable for the current usage pattern.

---

## Task 2: Add span-based flow name extraction to `_parse_trace`

**Risk:** M — changes how flow names are extracted, affects all downstream aggregation
**Intent:** Extract flow name from root span when labels are absent.
**File:** `service.py` — `_parse_trace` method (~line 272-325)
**Scope:** "Done" means `_parse_trace` returns a `flow_name` for traces that have a workflow span, even when `metadata.labels` is empty.

**Reference implementation:** Match `langwatch.py:53` span naming — the tracer sets the root span name to the flow name.

**Change:** After line 292 (where `flow_name` is extracted from labels), add fallback:
```python
# Fallback: extract from root workflow span name
if flow_name is None:
    spans = trace.get("spans") or []
    for span in spans:
        if span.get("type") == "workflow":
            flow_name = span.get("name")
            break
```

Note: The `spans` variable is already used later (line 303) for model extraction. Move the `spans = trace.get("spans") or []` line BEFORE the flow_name extraction so it's available for both.

**Acceptance criteria:**
- [ ] When `metadata.labels` has `"Flow: MyBot"`, `flow_name` is `"MyBot"` (existing behavior preserved)
- [ ] When `metadata.labels` is empty but spans contain a `type: "workflow"` span with `name: "MyBot"`, `flow_name` is `"MyBot"`
- [ ] When both labels and spans are absent, `flow_name` is `None`
- [ ] The `spans` variable is reused for model extraction (no duplicate `.get("spans")`)

**Impact analysis:** `_parse_trace` is called by `_aggregate_with_metadata` (line ~440) and `fetch_flow_runs` (line ~680). Both use `parsed["flow_name"]` for grouping. The change is transparent — they receive a flow_name where they previously received None.

**Rollback:** Remove the fallback block.

---

## Task 3: Add span-based fallback to `_filter_by_ownership`

**Risk:** M — changes the filtering logic that determines which traces are shown
**Intent:** Match traces to flows using span name when labels are absent.
**File:** `service.py` — `_filter_by_ownership` method (~line 396-408)
**Scope:** "Done" means traces with no labels but a matching workflow span name are included in results.

**Change:** In the filter loop (lines 396-408), add the same span-based fallback:
```python
for trace in traces:
    metadata = trace.get("metadata") or {}
    labels: list = metadata.get("labels") or []
    flow_name = next(
        (lbl[6:] for lbl in labels if isinstance(lbl, str) and lbl.startswith("Flow: ")),
        None,
    )
    # Fallback: root workflow span name
    if flow_name is None:
        for span in trace.get("spans", []):
            if span.get("type") == "workflow":
                flow_name = span.get("name")
                break
    if flow_name in allowed_names:
        filtered.append(trace)
```

**Acceptance criteria:**
- [ ] Traces with `labels: ["Flow: MyBot"]` are matched (existing behavior)
- [ ] Traces with `labels: []` but `spans: [{type: "workflow", name: "MyBot"}]` are matched
- [ ] Traces with neither labels nor matching span name are excluded
- [ ] `flow_name_map` lookup uses the same name regardless of source (label or span)

**Sync pair:** Must agree with `_parse_trace` (Task 2) on how flow names are extracted from spans.

**Rollback:** Revert the filter loop to label-only matching.

---

## Task 4: Filter to workflow-type traces only

**Risk:** M — changes which traces are counted, directly affects invocation count
**Intent:** Prevent over-counting by filtering out per-component traces.
**File:** `service.py` — `_fetch_from_langwatch` method (~line 225-268)
**Scope:** "Done" means only traces whose root span has `type: "workflow"` are passed downstream.

**Change:** After `_fetch_all_pages` returns raw traces (line ~263), add a filter:
```python
raw_traces = await self._fetch_all_pages(api_key, start_ms, end_ms)

# Filter to workflow-type traces only (avoid counting per-component traces)
raw_traces = [
    t for t in raw_traces
    if any(s.get("type") == "workflow" for s in (t.get("spans") or []))
]
```

**Acceptance criteria:**
- [ ] Traces with a `type: "workflow"` span are kept
- [ ] Traces with only `type: "component"` or `type: "llm"` spans are excluded
- [ ] A flow execution that previously produced 4 traces now produces 1 counted invocation
- [ ] If `includeSpans` was not set (backward compat), traces with no spans are kept (don't filter what you can't inspect)

**For the last criterion, add a guard:**
```python
raw_traces = [
    t for t in raw_traces
    if not t.get("spans") or any(s.get("type") == "workflow" for s in t["spans"])
]
```

**Impact analysis:** `_fetch_from_langwatch` feeds into `get_usage_summary` (line ~555) and indirectly into `_filter_by_ownership` and `_aggregate_with_metadata`. Fewer traces means more accurate invocation counts.

**Rollback:** Remove the filter list comprehension.

---

## Task 5: Add diagnostic logging

**Risk:** L — logging only, no behavior change
**Intent:** Make it easier to debug trace matching issues in the future.
**File:** `service.py` — `_filter_by_ownership` and `_fetch_from_langwatch`

**Changes:**

In `_fetch_from_langwatch`, after the workflow filter (Task 4):
```python
logger.debug("Fetched %d traces from LangWatch (%d after workflow filter)", len(all_traces), len(raw_traces))
```

In `_filter_by_ownership`, after the filter loop:
```python
dropped = len(traces) - len(filtered)
if dropped:
    logger.debug("Ownership filter: kept %d of %d traces (%d dropped, no flow match)", len(filtered), len(traces), dropped)
```

**Acceptance criteria:**
- [ ] Debug log shows trace count before/after workflow filter
- [ ] Debug log shows how many traces were dropped by ownership filter
- [ ] Logs appear when `LANGFLOW_LOG_LEVEL=debug`

**Rollback:** Remove the logging lines.

---

## Task 6: Verify — Usage Dashboard Shows Data

**Intent:** Confirm the fix works end-to-end.
**Action:**
1. Restart the backend (code changes picked up)
2. Call `GET /api/v1/usage/` with auth token
3. Confirm `total_invocations > 0` and `flows` is non-empty
4. Open http://localhost:13000/usage in browser — confirm summary cards show non-zero values
5. Take a Playwright screenshot as evidence

**Acceptance criteria:**
- [ ] API returns `total_invocations > 0`
- [ ] API returns at least one flow in `flows[]`
- [ ] Flow name matches the flow that was executed
- [ ] Usage page renders summary cards with non-zero data

---

## Appendix

**Input source:** `Research/bugs/trace-flow-matching-gap/research.md`

**Out of scope:**
- Null token counts (separate OTEL instrumentation issue)
- Tracer-side metadata fix (future phase)
- Redis caching (already documented as dead code)
- LangWatch server-side metadata promotion bug

**Technical decisions:**
- Span-based matching chosen over tracer fix because it works retroactively with existing trace data
- Workflow-type filter prevents N+1 over-counting (1 workflow + N component traces per execution)
- Labels remain the primary extraction path for forward compatibility when LangWatch fixes their metadata surfacing
