---
skill: serious-research
slug: trace-flow-matching-gap
status: active
parent: Research/bugs/trace-flow-matching-gap
created: 2026-03-17
---

# Thread 1: How the LangBuilder Tracer Sends Trace Metadata to LangWatch

## 1. Overview

The LangWatch integration lives in a single file:

**`src/backend/base/langflow/services/tracing/langwatch.py`** (211 lines)

It uses the **LangWatch Python SDK v0.2.19** (constraint: `>=0.2.11,<0.3.0`), which is the **OpenTelemetry-based SDK** (not the older REST-based version). Evidence: the tracer directly imports `opentelemetry.sdk.trace.TracerProvider`, `BatchSpanProcessor`, and `OTLPSpanExporter`, and calls `langwatch.setup(skip_open_telemetry_setup=True)`.

---

## 2. Tracer Initialization (`__init__`, lines 31-58)

```python
def __init__(self, trace_name: str, trace_type: str, project_name: str, trace_id: UUID):
```

**Parameters received from `TracingService._initialize_langwatch_tracer()`** (service.py:179-185):
- `trace_name` = `trace_context.run_name` = `f"{self.flow_name} - {self.flow_id}"` (set in `Graph.initialize_run()`, lfx graph/base.py:665)
- `trace_type` = `"chain"` (hardcoded in service.py:181)
- `project_name` = `trace_context.project_name` (defaults to env `LANGCHAIN_PROJECT` or `"Langflow"`)
- `trace_id` = `trace_context.run_id` (a UUID, set from `Graph._run_id`)

**What the constructor does:**
1. Stores params as instance attributes
2. **Parses `flow_id`** from `trace_name`: `self.flow_id = trace_name.split(" - ")[-1]` (line 36)
   - If `trace_name` = `"My Flow - abc-123-def"`, then `flow_id` = `"abc-123-def"`
3. Calls `setup_langwatch()` (line 39)
4. Creates the trace: `self.trace = self._client.trace(trace_id=str(self.trace_id), tracer_provider=self.tracer_provider)` (line 44)
5. Enters the trace context: `self.trace.__enter__()` (line 45)
6. **Updates root span** with cleaned name (lines 48-55):
   - Parses `name_without_id` = everything before the last ` - ` in `trace_name` (i.e., just the flow name)
   - Falls back to `project_name` if `name_without_id == "None"`
   - Sets: `span_id=f"{self.flow_id}-{nanoid(6)}"`, `name=name_without_id`, `type="workflow"`

**Notable:** The LangWatch tracer does **NOT** receive `user_id` or `session_id` as constructor params (unlike LangFuse, Opik, etc.). The `BaseTracer.__init__` signature accepts them, but `LangWatchTracer.__init__` does not declare them.

---

## 3. `setup_langwatch()` (lines 64-96)

**Gate:** Returns `False` if `LANGWATCH_API_KEY` not in env.

**First-time initialization (class-level singleton pattern):**
- Creates a dedicated `TracerProvider` with:
  - `Resource(attributes={"service.name": "langflow"})`
  - `OTLPSpanExporter` pointed at `{endpoint}/api/otel/v1/traces` with `Bearer {api_key}` auth
  - `BatchSpanProcessor` wrapping the exporter
- Stores it as `LangWatchTracer.tracer_provider` (class variable, shared across instances)
- Calls `langwatch.setup(api_key=..., endpoint_url=..., skip_open_telemetry_setup=True)`
  - `skip_open_telemetry_setup=True` prevents the SDK from touching the global OTEL provider (to avoid interfering with FastAPIInstrumentor)

**Every time:** Sets `self._client = langwatch` (the module itself).

**`self._client` is the `langwatch` module**, not a client instance. The module-level `langwatch.trace()` and `langwatch.setup()` functions are used.

---

## 4. `add_trace()` — Per-Component Span Creation (lines 98-132)

Called once per component/vertex in the flow graph.

```python
def add_trace(self, trace_id, trace_name, trace_type, inputs, metadata=None, vertex=None):
```

**Key behaviors:**

1. **thread_id injection** (lines 112-113):
   ```python
   if "session_id" in inputs and inputs["session_id"] != self.flow_id:
       self.trace.update(metadata=(self.trace.metadata or {}) | {"thread_id": inputs["session_id"]})
   ```
   - Only sets `thread_id` if the component's inputs contain a `session_id` AND it differs from `self.flow_id`
   - This means: if the user provides a custom session_id, it becomes the thread_id; otherwise, no thread_id is set
   - **IMPORTANT:** This is set on the TRACE, not the span — it's trace-level metadata

2. **Span creation** (lines 123-131):
   - `span_id` = `f"{trace_id}-{nanoid(6)}"` (globally unique)
   - `name` = component name without the `(id)` suffix
   - `type` = `"component"` (hardcoded)
   - `parent` = last incoming edge's span, or root_span if no predecessors
   - `input` = converted inputs (via `_convert_to_langwatch_types`)

---

## 5. `end_trace()` — Per-Component Span Completion (lines 134-146)

```python
def end_trace(self, trace_id, trace_name, outputs=None, error=None, logs=()):
```

Ends the span for a specific component. Sets `output` and `error` on the span. Does **not** set any additional metadata.

---

## 6. `end()` — Trace Completion (lines 148-170)

```python
def end(self, inputs, outputs, error=None, metadata=None):
```

Called by `TracingService._end_all_tracers()` (service.py:310-322), which passes:
- `inputs` = `trace_context.all_inputs` (aggregated from all components)
- `outputs` = `trace_context.all_outputs` (aggregated from all components)
- `error` = any error
- `metadata` = the `outputs` dict passed to `end_tracers()`, which is `graph.metadata | {actual outputs}` (graph/base.py:701)

**`graph.metadata`** contains (graph/base.py:911-924):
```python
{
    "start_time": "...",
    "end_time": "...",
    "time_elapsed": "...",
    "flow_id": self.flow_id,
    "flow_name": self.flow_name,
}
```

**What `end()` does:**

1. Ends the root span with input/output (lines 157-161)
2. **Labels injection** (lines 163-164):
   ```python
   if metadata and "flow_name" in metadata:
       self.trace.update(metadata=(self.trace.metadata or {}) | {"labels": [f"Flow: {metadata['flow_name']}"]})
   ```
   - Sets a label like `"Flow: My Flow Name"`
   - **CRITICAL:** This REPLACES any existing `labels` key in metadata (uses `|` dict merge, which overwrites)
   - This PRESERVES `thread_id` if it was set earlier (because `|` only overwrites the `labels` key, not `thread_id`)
3. **Exports the trace** (lines 166-170):
   - Checks `self.trace.api_key or self._client._api_key`
   - Calls `self.trace.__exit__(None, None, None)` to flush the trace to LangWatch via OTEL
   - Catches `ValueError` for "token was created in a different Context" errors

---

## 7. `get_langchain_callback()` (lines 206-210)

Returns `self.trace.get_langchain_callback()` — delegates to the LangWatch SDK's built-in LangChain callback handler. This allows LangChain LLM calls within components to be automatically traced as child spans.

---

## 8. Complete Metadata Inventory

### Trace-Level Metadata

| Field | Value | Set Where | When |
|-------|-------|-----------|------|
| `trace_id` | `str(UUID)` — the graph run ID | `__init__:44` via `self._client.trace(trace_id=...)` | Trace creation |
| `thread_id` | `inputs["session_id"]` (only if != flow_id) | `add_trace:113` via `self.trace.update(metadata={"thread_id": ...})` | First component with session_id |
| `labels` | `[f"Flow: {flow_name}"]` | `end:164` via `self.trace.update(metadata={"labels": [...]})` | Trace end |

### Root Span Attributes

| Field | Value | Set Where | When |
|-------|-------|-----------|------|
| `span_id` | `f"{flow_id}-{nanoid(6)}"` | `__init__:52` via `root_span.update(span_id=...)` | Trace creation |
| `name` | Flow name (without ID suffix) | `__init__:53` via `root_span.update(name=...)` | Trace creation |
| `type` | `"workflow"` | `__init__:54` via `root_span.update(type=...)` | Trace creation |
| `input` | Converted aggregated inputs | `end:158` via `root_span.end(input=...)` | Trace end |
| `output` | Converted aggregated outputs | `end:159` via `root_span.end(output=...)` | Trace end |
| `error` | Exception if any | `end:160` via `root_span.end(error=...)` | Trace end |

### Per-Component Span Attributes

| Field | Value | Set Where | When |
|-------|-------|-----------|------|
| `span_id` | `f"{vertex_id}-{nanoid(6)}"` | `add_trace:125` | Component start |
| `name` | Component name (without ID suffix) | `add_trace:126` | Component start |
| `type` | `"component"` | `add_trace:127` | Component start |
| `parent` | Previous node's span or root_span | `add_trace:128` | Component start |
| `input` | Converted component inputs | `add_trace:129` | Component start |
| `output` | Converted component outputs | `end_trace:146` | Component end |
| `error` | Exception if any | `end_trace:146` | Component end |

### OTEL Resource Attributes

| Field | Value | Set Where |
|-------|-------|-----------|
| `service.name` | `"langflow"` | `setup_langwatch:76` |

### OTEL Export Configuration

| Field | Value | Set Where |
|-------|-------|-----------|
| Endpoint | `{LANGWATCH_ENDPOINT}/api/otel/v1/traces` | `setup_langwatch:78` |
| Auth header | `Bearer {LANGWATCH_API_KEY}` | `setup_langwatch:78` |

---

## 9. What is NOT Sent

These fields exist in the tracing system but are **NOT** forwarded to LangWatch:

| Field | Available In | Why Not Sent |
|-------|-------------|-------------|
| `user_id` | `TraceContext.user_id` | LangWatch tracer constructor does not accept `user_id` |
| `session_id` (directly) | `TraceContext.session_id` | Not passed to constructor; only discovered via component inputs |
| `flow_id` (as metadata) | `self.flow_id` (parsed from trace_name) | Used only for span_id prefix, not set as trace metadata |
| `project_name` | `self.project_name` | Not set as trace metadata (OTEL resource has `service.name` = `"langflow"` instead) |

---

## 10. Lifecycle Summary

```
Graph.initialize_run()
  |
  +--> TracingService.start_tracers(run_id, run_name="FlowName - flow_id", ...)
         |
         +--> _initialize_langwatch_tracer()
                |
                +--> LangWatchTracer.__init__(trace_name, "chain", project_name, trace_id)
                       |
                       +--> setup_langwatch()         # OTEL provider + langwatch.setup()
                       +--> langwatch.trace(trace_id)  # Create trace context
                       +--> root_span.update(...)       # Set span_id, name, type="workflow"

For each component:
  TracingService.trace_component()
    |
    +--> tracer.add_trace(vertex_id, name, type, inputs, metadata, vertex)
           |
           +--> [conditionally] trace.update(metadata={"thread_id": session_id})
           +--> trace.span(span_id, name, type="component", parent, input)
    |
    ... component executes ...
    |
    +--> tracer.end_trace(vertex_id, name, outputs, error)
           |
           +--> span.end(output, error)

Graph.end_all_traces()
  |
  +--> TracingService.end_tracers(outputs | graph.metadata)
         |
         +--> _end_all_tracers(trace_context, outputs)
                |
                +--> tracer.end(all_inputs, all_outputs, error, metadata={..., flow_name: "..."})
                       |
                       +--> root_span.end(input, output, error)
                       +--> trace.update(metadata={"labels": ["Flow: FlowName"]})
                       +--> trace.__exit__()  # Flush to LangWatch via OTEL
```

---

## 11. Key Observations and Potential Issues

### 11.1 thread_id is Conditionally Set and Depends on Component Inputs

The `thread_id` is NOT set from `TraceContext.session_id` directly. Instead, it's discovered from the `inputs` dict of individual components (line 112-113). This means:

- If no component has `session_id` in its inputs, **no thread_id is set at all**
- If the session_id equals the flow_id (default behavior when user doesn't specify a session), **no thread_id is set**
- Multiple components could each trigger `trace.update()` with `thread_id`, but since they all use the same session_id, only the value from the last call matters (dict merge)

### 11.2 Labels Overwrite Problem

Line 164: `{"labels": [f"Flow: {metadata['flow_name']}"]}` creates a fresh single-element list. If any previous code had set labels on the trace metadata, they would be overwritten (not appended). In the current codebase, no other code sets labels, so this is not currently a problem — but it's fragile.

### 11.3 flow_id is Not Sent as Trace Metadata

The `flow_id` is parsed from `trace_name` (line 36) and used as a prefix for `span_id` values, but it is **never set as trace-level metadata**. LangWatch receives it only implicitly through span_id strings like `"abc-123-def-xK9mPq"`.

### 11.4 session_id vs thread_id Naming

The codebase uses `session_id` internally, but maps it to `thread_id` in LangWatch metadata. This is the LangWatch convention — threads group related traces in the LangWatch UI.

### 11.5 SDK Architecture: Hybrid OTEL

The tracer creates its own `TracerProvider` with `skip_open_telemetry_setup=True` to avoid conflicts with FastAPI's global OTEL instrumentation. This means:
- LangWatch SDK uses OTEL internally for span management
- But the tracer manages its own export pipeline (dedicated `BatchSpanProcessor` + `OTLPSpanExporter`)
- The `langwatch.trace()` and `langwatch.span()` APIs are wrappers around OTEL spans with LangWatch-specific attributes

### 11.6 No Explicit user_id

Unlike LangFuse and Opik tracers (which receive `user_id` and `session_id` in their constructors), the LangWatch tracer constructor signature does **not** accept these parameters (line 31). The `TracingService._initialize_langwatch_tracer()` (service.py:179-185) only passes the 4 base params. Compare with LangFuse (service.py:196-198) which also passes `user_id` and `session_id`.
