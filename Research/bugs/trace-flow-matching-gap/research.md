---
skill: serious-research
slug: trace-flow-matching-gap
status: done
parent:
created: 2026-03-17
classification: Bug
scope: Codebase only
mode: Deep
---

# Trace-to-Flow Matching Gap

## Summary

The Usage dashboard shows zero data despite LangWatch traces existing because of a metadata visibility gap. The tracer sets `metadata.labels: ["Flow: <name>"]` via `trace.update()`, which serializes labels into root span OTEL attributes. But the LangWatch search API's `metadata` field reflects OTEL Resource attributes only — span-level metadata is invisible. The service's `_filter_by_ownership` looks for labels in the API's metadata, finds nothing, and silently drops all traces.

The flow name IS available in the **root span name** (where `type == "workflow"`). A service-side fix can extract it from there without touching the tracer.

Additionally, one flow execution creates **multiple traces** (1 workflow + N component traces), which would cause over-counting if not filtered.

## Root Cause

**Three-layer failure:**

1. **Tracer sends labels correctly** — `langwatch.py:163-164` calls `trace.update(metadata={"labels": ["Flow: <name>"]})`. The LangWatch SDK serializes this as JSON into the root span's `"metadata"` OTEL attribute.

2. **LangWatch API doesn't surface it** — The search API's `metadata` field contains only OTEL Resource attributes (`service.name`, `telemetry.sdk.*`). Span-level attributes like the serialized metadata JSON are not promoted to the trace-level `metadata` field.

3. **Service expects it in metadata** — `_filter_by_ownership` extracts flow names from `trace["metadata"]["labels"]`, finds `labels: []`, matches nothing, drops everything.

## What IS Available in the API

From direct API testing (Thread 3):

| Field | Available? | Contains |
|-------|-----------|----------|
| `trace.metadata.labels` | NO (empty) | Should have `["Flow: <name>"]` |
| `trace.metadata.thread_id` | NO | Should have session ID |
| `trace.spans[0].name` | YES | Flow name (e.g., "Talk with Haiku") |
| `trace.spans[0].type` | YES | "workflow" for flow traces, "component" for others |
| `trace.spans[0].params.deprecated.span.id` | YES | `{flow_id}-{nanoid}` |
| `trace.metrics.total_time_ms` | YES | Execution time |
| `trace.metrics.prompt_tokens` | NO (null) | Separate issue — OTEL instrumentation gap |

## Multi-Trace Problem

One flow execution creates **N+1 traces**: 1 workflow trace + N component traces. Only the workflow trace (root span `type: "workflow"`) represents the full execution. Component traces should be filtered out to avoid over-counting invocations.

## Recommended Fix: Service-Side, Minimal

**No tracer changes needed.** Modify the service to read flow name from spans.

### Changes Required

**1. Add `includeSpans` to fetch request** (`_fetch_all_pages`):
```python
payload["includeSpans"] = True
```

**2. Add span-based flow name extraction** (`_parse_trace`):
```python
# Primary: labels (existing)
flow_name = next((lbl[6:] for lbl in labels if lbl.startswith("Flow: ")), None)
# Fallback: root span name
if flow_name is None:
    for span in trace.get("spans", []):
        if span.get("type") == "workflow":
            flow_name = span.get("name")
            break
```

**3. Filter to workflow traces only** (new, in `_fetch_from_langwatch` or `_filter_by_ownership`):
```python
# Only count workflow-type traces, not per-component traces
traces = [t for t in raw_traces if any(
    s.get("type") == "workflow" for s in t.get("spans", [])
)]
```

**4. Add diagnostic logging** when traces are dropped:
```python
logger.debug("Dropped %d traces with no flow match (of %d total)", dropped, total)
```

### Files to Modify
- `src/backend/base/langflow/services/langwatch/service.py` — `_fetch_all_pages`, `_parse_trace`, `_filter_by_ownership`

### Future Phase (Tracer)
- Pass `metadata={"labels": [...], "flow_id": self.flow_id}` at trace creation time
- Add `flow_id` to trace metadata for ID-based matching
- File bug with LangWatch about `trace.update(metadata=...)` not appearing in search API

## Separate Issue: Null Token Counts
Token counts (`prompt_tokens`, `completion_tokens`) are null in all traces. This is an independent issue in the LangWatch SDK's OTEL instrumentation — it doesn't capture token usage from LangChain callbacks. Should be tracked separately.

## Sync Pairs

| Function A | Function B | Must agree on |
|-----------|-----------|---------------|
| `langwatch.py:163` trace.update labels format | `service.py _filter_by_ownership` label parsing | `"Flow: <name>"` prefix |
| `langwatch.py:44` trace creation | `service.py _parse_trace` span extraction | Root span structure |
| `langwatch.py:53` span naming | `service.py _filter_by_ownership` name matching | Flow name string |

## References

| File | Key lines | Role |
|------|-----------|------|
| `services/tracing/langwatch.py` | 44 (trace create), 53 (span name), 113 (thread_id), 163-164 (labels) | LangBuilder tracer |
| `services/langwatch/service.py` | 181 (fetch), 271-324 (parse), 340-420 (filter), 534-570 (summary) | Usage service |

### Thread files
- `thread-1-tracer.md` — How the tracer sets metadata (labels at line 164, thread_id at line 113)
- `thread-2-usage-service.md` — How the service filters (7 gaps identified)
- `thread-3-real-data.md` — What the API actually returns (root span has flow name)

### Persona review
- **Senior Engineer** — Confirmed root cause. Recommended minimal service-side fix first, tracer fix as Phase 2. Flagged over-counting risk from multi-trace-per-execution.
