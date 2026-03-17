---
skill: serious-research
slug: trace-flow-matching-gap
status: active
parent: Research/bugs/trace-flow-matching-gap
created: 2026-03-17
---

# Thread 3: Real API Data -- What LangWatch Actually Returns

## Summary

**Critical finding:** The LangWatch traces arriving via the API contain **NO flow_id, NO flow_name, NO labels, and NO thread_id** in the `metadata` field. The tracer code INTENDS to send `labels` (via `trace.update(metadata={"labels": [...]})`) and `thread_id` (via `trace.update(metadata={"thread_id": ...})`), but these are NOT appearing in the API response metadata. The metadata only contains OpenTelemetry SDK boilerplate (`telemetry.sdk.*`, `service.name`).

However, the **root span name** IS the flow name (e.g., "Talk with Haiku") and the **root span's `deprecated.span.id`** contains the flow_id. These are usable for matching.

---

## 1. Raw Trace Data from LangWatch API

### API Call
```bash
POST https://app.langwatch.ai/api/traces/search
Body: {"startDate": <24h_ago>, "endDate": <now>, "pageSize": 5, "includeSpans": true}
```

### Trace Structure (4 traces found for the same flow execution)

Each trace has these top-level fields:
```json
{
  "trace_id": "4c3b572d6a20c6e1a1ce2474ac1c2000",
  "project_id": "project_goc1f_znDC5J_vGI0iHtQ",
  "timestamps": {
    "started_at": 1773772336430,
    "inserted_at": 1773772342112,
    "updated_at": 1773772342112
  },
  "error": null,
  "indexing_md5s": ["760fbbde37b41df8a7cc515d70fdc77c"],
  "metadata": {
    "telemetry.sdk.language": "python",
    "telemetry.sdk.name": "opentelemetry",
    "telemetry.sdk.version": "1.39.1",
    "service.name": "langflow"
  },
  "events": [],
  "evaluations": [],
  "spans": [...],
  "input": { "value": "..." },
  "output": { "value": "..." },
  "metrics": {
    "first_token_ms": null,
    "total_time_ms": 2258,
    "prompt_tokens": null,
    "completion_tokens": null,
    "reasoning_tokens": null,
    "cache_read_input_tokens": null,
    "cache_creation_input_tokens": null,
    "tokens_estimated": false
  }
}
```

### Key Observation: NO flow-identifying metadata

The `metadata` field contains ONLY OpenTelemetry SDK info:
```json
{
  "telemetry.sdk.language": "python",
  "telemetry.sdk.name": "opentelemetry",
  "telemetry.sdk.version": "1.39.1",
  "service.name": "langflow"
}
```

**Missing from metadata:**
- `thread_id` -- NOT present
- `labels` -- NOT present
- `customer_id` -- NOT present
- `flow_id` -- NOT present
- `flow_name` -- NOT present

---

## 2. Trace-Level Fields -- Complete Inventory

| Field | Present | Value Example | Flow-Identifying? |
|-------|---------|---------------|-------------------|
| `trace_id` | Yes | `"4c3b572d..."` | No (auto-generated) |
| `project_id` | Yes | `"project_goc1f_..."` | No (org-level) |
| `timestamps` | Yes | `{started_at, inserted_at, updated_at}` | No |
| `error` | Yes | `null` | No |
| `indexing_md5s` | Yes | `["760fbb..."]` | No |
| `metadata` | Yes | Only OTEL SDK info | **NO -- missing flow data** |
| `events` | Yes | `[]` | No |
| `evaluations` | Yes | `[]` | No |
| `spans` | Yes | Array of span objects | **YES -- see below** |
| `input` | Yes | Stringified JSON | Partially (contains component names with IDs) |
| `output` | Yes | Stringified JSON | Partially (contains component names with IDs) |
| `metrics` | Yes | Token/time metrics | No |

---

## 3. Span Data -- Where Flow Info ACTUALLY Lives

### Root Span (type: "workflow") -- THE KEY

The workflow root span DOES contain flow-identifying information:

```json
{
  "span_id": "571cdc5e196f1697",
  "trace_id": "4c3b572d6a20c6e1a1ce2474ac1c2000",
  "name": "Talk with Haiku",        // <-- FLOW NAME IS HERE
  "type": "workflow",                // <-- Root span type
  "params": {
    "deprecated": {
      "span": {
        "id": "aebfb10c-c4c5-4f72-ba37-7f048b501bae-vivivT"
        // ^^ This is flow_id + nanoid suffix
      }
    },
    "scope": {
      "name": "langwatch",
      "version": "0.2.19"
    },
    "_keys": [
      "deprecated.span.id",
      "scope.name",
      "scope.version"
    ]
  }
}
```

**Critical findings from root span:**
1. `span.name` = `"Talk with Haiku"` -- This is the flow name (set in tracer line 49: `name_without_id`)
2. `span.params.deprecated.span.id` = `"aebfb10c-c4c5-4f72-ba37-7f048b501bae-vivivT"` -- This is `{flow_id}-{nanoid}` (set in tracer line 52)
3. `span.type` = `"workflow"` -- Always "workflow" for root span

### Component Spans (type: "component")

Each flow component gets its own span:

```json
{
  "span_id": "0f567cf6abb12f6f",
  "name": "Chat Input",          // Component display name
  "type": "component",
  "params": {
    "deprecated": {
      "span": {
        "id": "ChatInput-2aelP-UyP55n"   // component_id + nanoid
      }
    }
  }
}
```

Component names found: `"Chat Input"`, `"Agent"`, `"Chat Output"`

### LangChain Internal Spans (type: "chain", "llm")

These are LangChain execution spans within the Agent component:
- `"AgentExecutor"` (type: chain)
- `"RunnableSequence"` (type: chain)
- `"ChatPromptTemplate"` (type: chain)
- `"llm"` (type: llm, model: "anthropic/claude-haiku-4-5-20251001")
- `"ToolsAgentOutputParser"` (type: chain)

---

## 4. One Flow Execution = Multiple Traces

A single flow execution produced **4 separate traces** (one per component + one for the overall flow):

| Trace | Root Span | Type | Duration |
|-------|-----------|------|----------|
| `4c3b572d...` | "Talk with Haiku" | workflow | 2258ms |
| `aaff1a81...` | "Chat Input" | component | 11ms |
| `3177208a...` | "Agent" | component | 1619ms |
| `f0703ba9...` | "Chat Output" | component | 6ms |

**This is the core problem for matching**: A single flow execution creates 4 independent traces with NO shared identifier in the API-visible metadata.

---

## 5. What the Tracer INTENDS to Send vs What ACTUALLY Arrives

### Intended: Labels with flow name

**Code** (`langwatch.py` line 163-164):
```python
if metadata and "flow_name" in metadata:
    self.trace.update(metadata=(self.trace.metadata or {}) | {"labels": [f"Flow: {metadata['flow_name']}"]})
```

**What this does:** Calls `trace.update(metadata={"labels": ["Flow: Talk with Haiku"]})`, which sets `self.metadata["labels"] = ["Flow: Talk with Haiku"]` on the trace Python object, then serializes it as a JSON string into the root span's OTEL attributes (`span.set_attributes({"metadata": json.dumps(...)})`)

**What arrives in API:** The `metadata` field on the trace does NOT contain `labels`. The LangWatch server-side apparently doesn't parse the serialized metadata JSON from the span attributes back into the trace's metadata. The metadata only shows the OTEL Resource attributes (`service.name`, `telemetry.sdk.*`).

### Intended: thread_id from session_id

**Code** (`langwatch.py` line 112-113):
```python
if "session_id" in inputs and inputs["session_id"] != self.flow_id:
    self.trace.update(metadata=(self.trace.metadata or {}) | {"thread_id": inputs["session_id"]})
```

**What arrives in API:** No `thread_id` in metadata. Same problem -- the metadata set via `trace.update()` goes into a JSON-serialized span attribute, not directly into the trace-level metadata that the API exposes.

### Why the mismatch?

The LangWatch SDK's `trace.update(metadata=...)` works by:
1. Updating `self.metadata` dict on the Python object
2. Serializing it as JSON into the root span's OTEL attributes: `span.set_attributes({"metadata": json.dumps(self.metadata)})`

But the **trace-level `metadata`** returned by the API comes from the **OTEL Resource attributes** (`service.name`, `telemetry.sdk.*`), NOT from the span-level serialized metadata attribute.

This means:
- The metadata set via `trace.update()` is embedded in the span's OTEL attributes as a serialized JSON string
- It's NOT promoted to the trace-level metadata visible in the API response
- **The labels and thread_id ARE being sent** -- they're just buried in the root span's OTEL attributes as a JSON string, and the LangWatch server may or may not be parsing them

---

## 6. Available API Filter Options

The LangWatch search API supports these filter keys (discovered via error response):

```
topics.topics
topics.subtopics
metadata.user_id
metadata.thread_id        <-- Supported but NO data
metadata.customer_id      <-- Supported but NO data
metadata.labels           <-- Supported but NO data
metadata.key
metadata.value
metadata.prompt_ids
traces.origin
traces.error
spans.type
spans.model
evaluations.evaluator_id
evaluations.evaluator_id.guardrails_only
evaluations.passed
evaluations.score
evaluations.state
evaluations.label
events.event_type
events.metrics.key
events.metrics.value
events.event_details.key
annotations.hasAnnotation
```

**Confirmed:** Searching by `metadata.labels: ["Flow: Talk with Haiku"]` returns 0 results -- the labels are NOT being indexed.

---

## 7. What CAN Be Used to Match Traces to Flows (Today)

### Approach A: Root span name (RELIABLE)
- The root span with `type: "workflow"` has `name` = flow name
- Matching: Filter spans where `type == "workflow"` and `name == <flow_name>`
- Limitation: Only present on the "overall" trace, not the per-component traces

### Approach B: Root span's deprecated.span.id (PARTIALLY RELIABLE)
- Contains `{flow_id}-{nanoid}` (e.g., `"aebfb10c-c4c5-4f72-ba37-7f048b501bae-vivivT"`)
- The flow_id can be extracted by stripping the last 7 characters (dash + 6-char nanoid)
- Limitation: The nanoid makes exact matching impossible without prefix matching

### Approach C: Input/output parsing (FRAGILE)
- The overall trace's `input.value` is a JSON string containing component names like `"Chat Input (ChatInput-2aelP)"`
- Component IDs like `ChatInput-2aelP` are flow-specific
- Limitation: Extremely fragile, parsing nested JSON strings

### Approach D: Fix the tracer (RECOMMENDED)
- The tracer code already TRIES to send labels and thread_id
- The issue is that `trace.update(metadata=...)` doesn't actually populate the trace-level metadata the API returns
- Fix: Either use the correct LangWatch SDK mechanism for setting labels/thread_id, or set them as OTEL Resource attributes

---

## 8. LangWatch SDK's Proper Mechanism for Labels/Thread ID

Looking at the `attributes.py` in the LangWatch SDK:

```python
LangWatchCustomerId = "langwatch.customer.id"
LangWatchThreadId = "langwatch.thread.id"
LangWatchSessionId = "langwatch.session.id"
```

These are **OTEL span attributes**, not trace metadata keys. The correct way to set thread_id might be:
```python
self.trace.root_span.set_attributes({
    AttributeKey.LangWatchThreadId: session_id
})
```

But the current code uses:
```python
self.trace.update(metadata={"thread_id": session_id})
```

The SDK puts `metadata` into a JSON-serialized attribute on the span. The LangWatch server then needs to parse this and extract `thread_id` and `labels` from it. Whether it does this correctly is the question.

---

## 9. Definitive Conclusion

### Root Cause
The LangWatch tracer in LangBuilder sends flow-identifying information (labels, thread_id) via `trace.update(metadata=...)`, which serializes them into a JSON attribute on the root OTEL span. But the LangWatch API's `metadata` field for traces reflects the OTEL **Resource** attributes (service.name, SDK info), NOT the span-level metadata.

### The GAP
```
Tracer code sets:    trace.update(metadata={"labels": ["Flow: Talk with Haiku"], "thread_id": "..."})
SDK stores as:       root_span.set_attributes({"metadata": '{"labels":["Flow: Talk with Haiku"],"thread_id":"..."}'})
API returns:         metadata: {service.name: "langflow", telemetry.sdk.*: ...}  // NO labels, NO thread_id
```

### Available Workarounds
1. **Use root span name** = flow name (most reliable current approach)
2. **Use `deprecated.span.id` prefix** = flow_id (requires prefix matching)
3. **Fix the tracer** to use dedicated OTEL attributes (`langwatch.thread.id`, etc.) instead of embedding in serialized metadata JSON
