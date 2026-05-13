---
skill: serious-research
slug: trace-flow-matching-gap
status: active
parent: Research/bugs/trace-flow-matching-gap
created: 2026-03-17
---

# Thread 2: Usage Service — Trace Filtering & Flow Matching Logic

**Source file:** `src/backend/base/langflow/services/langwatch/service.py`
**Schemas file:** `src/backend/base/langflow/services/langwatch/schemas.py`

---

## Table of Contents

1. [Module Constants & Types](#1-module-constants--types)
2. [`_fetch_all_pages`](#2-_fetch_all_pages)
3. [`_fetch_from_langwatch`](#3-_fetch_from_langwatch)
4. [`_parse_trace`](#4-_parse_trace)
5. [`_filter_by_ownership` (KEY METHOD)](#5-_filter_by_ownership-key-method)
6. [`_aggregate_with_metadata`](#6-_aggregate_with_metadata)
7. [`get_usage_summary`](#7-get_usage_summary)
8. [End-to-End Data Flow Diagram](#8-end-to-end-data-flow-diagram)
9. [Identified Failure Modes & Gaps](#9-identified-failure-modes--gaps)

---

## 1. Module Constants & Types

```python
MAX_PAGES: int = 10
PAGE_SIZE: int = 1000
```

Maximum traces fetchable = `MAX_PAGES * PAGE_SIZE` = **10,000 traces**.

### `FlowMeta` dataclass

```python
@dataclass
class FlowMeta:
    flow_id: UUID
    user_id: UUID
    username: str
```

Carries DB-resolved metadata for a flow. Used to attach real UUIDs and owner info to aggregated results. Note: does **not** carry `created_at` — this matters for the collision tie-break logic (see section 5).

---

## 2. `_fetch_all_pages`

### Signature

```python
async def _fetch_all_pages(
    self,
    api_key: str,
    start_date_ms: int,
    end_date_ms: int,
) -> list[dict]
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | LangWatch API key (passed as header) |
| `start_date_ms` | `int` | Start of date range in epoch milliseconds |
| `end_date_ms` | `int` | End of date range in epoch milliseconds |

### Processing (step by step)

1. Initializes `all_traces: list[dict] = []` and `scroll_id: str | None = None`.
2. Loops up to `MAX_PAGES` (10) iterations.
3. On each iteration, builds the request payload:
   ```python
   payload = {
       "startDate": start_date_ms,
       "endDate": end_date_ms,
       "pageSize": PAGE_SIZE,  # 1000
   }
   ```
4. If `scroll_id` is not None (i.e., not the first page), adds `"scrollId": scroll_id` to payload.
5. Sends **POST** request to **`/api/traces/search`** with:
   - Headers: `{"X-Auth-Token": api_key}` (plus the default `Content-Type: application/json` from client config)
   - Body: the JSON payload
6. Calls `response.raise_for_status()` — on HTTP error:
   - **401 or 403** -> raises `LangWatchInvalidKeyError`
   - **Any other error status** -> raises `LangWatchUnavailableError`
7. Parses `response.json()` into `data`.
8. Extracts `page_traces = data.get("traces", [])` and extends `all_traces`.
9. Extracts `pagination = data.get("pagination", {})` and reads `scroll_id = pagination.get("scrollId")`.
10. **Stop conditions** (checked after extending traces):
    - `scroll_id` is `None` or falsy -> break
    - `page_traces` is empty -> break

### Expected LangWatch API Response Structure

```json
{
  "traces": [ { ... }, { ... } ],
  "pagination": {
    "scrollId": "opaque-string-or-null"
  }
}
```

### Output

Returns `list[dict]` — all raw trace dicts from all pages combined.

### Failure Modes

| Condition | Result |
|-----------|--------|
| API key invalid (401/403) | `LangWatchInvalidKeyError` raised |
| Server error (500, etc.) | `LangWatchUnavailableError` raised |
| Network timeout | Exception propagates to caller (handled by `get_usage_summary`) |
| > 10,000 traces in range | **Silent truncation** — only first 10 pages returned, no warning logged |
| Response missing `"traces"` key | Returns empty list (graceful via `.get("traces", [])`) |
| Response missing `"pagination"` key | `scroll_id` becomes `None`, loop breaks after first page |

---

## 3. `_fetch_from_langwatch`

### Signature

```python
async def _fetch_from_langwatch(
    self,
    params: UsageQueryParams,
    api_key: str,
) -> list[dict]
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `params` | `UsageQueryParams` | Contains `from_date`, `to_date`, `user_id`, `sub_view` |
| `api_key` | `str` | LangWatch API key |

### Processing (step by step)

1. Extracts `params.from_date` and `params.to_date`.
2. **Date conversion**: If `from_date` / `to_date` is a `date` (not `datetime`), wraps it in a `datetime` at midnight UTC. If already a `datetime`, uses as-is. If `None`, remains `None`.
3. Converts to epoch milliseconds:
   - `start_ms`: `int(from_dt.timestamp() * 1000)` if set, else **`0`** (epoch start).
   - `end_ms`: `int(to_dt.timestamp() * 1000)` if set, else **current time in ms**.
4. Delegates to `_fetch_all_pages(api_key, start_ms, end_ms)`.

### Output

Returns `list[dict]` — the raw trace list from `_fetch_all_pages`.

### Failure Modes

| Condition | Result |
|-----------|--------|
| `from_date` is `None` | `start_ms` = 0, meaning fetch from epoch start — potentially huge range |
| `to_date` is `None` | `end_ms` = current time |
| **`params.user_id` and `params.sub_view` are completely ignored** | These fields are never passed to LangWatch — filtering happens later |

### Key Observation

The LangWatch API request does **not** filter by flow, user, or sub_view. It fetches **all** traces in the date range for the entire API key (org). All filtering is done client-side in subsequent methods.

---

## 4. `_parse_trace`

### Signature

```python
@staticmethod
def _parse_trace(trace: dict) -> dict | None
```

### Input

A single raw trace dict from the LangWatch API.

### Processing (step by step)

1. Extracts `metadata = trace.get("metadata") or {}`.
2. Extracts `labels: list = metadata.get("labels") or []`.
3. Extracts `metrics = trace.get("metrics") or {}`.
4. Extracts `timestamps = trace.get("timestamps") or {}`.
5. **Flow name extraction** — scans `labels` for the first string matching `"Flow: <name>"`:
   ```python
   flow_name = next(
       (lbl[6:] for lbl in labels if isinstance(lbl, str) and lbl.startswith("Flow: ")),
       None,
   )
   ```
   - Takes the first matching label only.
   - Strips the `"Flow: "` prefix (6 characters).
   - If no label matches, `flow_name = None`.
6. **Cost extraction**: `metrics.get("total_cost")` -> cast to `float`, default `0.0`.
7. **Token extraction**: `metrics.get("prompt_tokens")` and `metrics.get("completion_tokens")` — left as-is (may be `None`).
8. **Model extraction**: Iterates `trace.get("spans") or []`, takes the first span with a truthy `"model"` field.
9. **Timestamp extraction**: `timestamps.get("started_at")` -> cast to `int` if present.
10. **Error detection**: `trace.get("error") is not None` -> boolean `has_error`.

### Output

Returns a dict:

```python
{
    "trace_id": str,         # trace.get("trace_id", "")
    "flow_name": str | None, # extracted from "Flow: <name>" label, or None
    "cost_usd": float,       # from metrics.total_cost, default 0.0
    "prompt_tokens": int | None,
    "completion_tokens": int | None,
    "model": str | None,     # from first span with a model field
    "started_at_ms": int | None,
    "has_error": bool,
}
```

Or `None` if any `TypeError`, `ValueError`, or `AttributeError` is caught.

### Failure Modes

| Condition | Result |
|-----------|--------|
| `trace` is malformed (missing expected structure) | Returns `None` (caught by blanket except) |
| `metadata` is `None` | Defaults to `{}` — `labels` becomes `[]`, `flow_name` becomes `None` |
| `labels` is `None` | Defaults to `[]`, `flow_name` becomes `None` |
| `labels` contains non-string items | Skipped by `isinstance(lbl, str)` check |
| No label matches `"Flow: "` prefix | `flow_name = None` |
| `metrics` is `None` | Defaults to `{}` — cost = 0.0, tokens = None |
| No spans, or no span with `model` | `model = None` |
| `total_cost` is non-numeric string | `float()` raises `ValueError` -> returns `None` |

### Key Observations

- The `"Flow: "` prefix is **hardcoded** (6 chars). The match is **case-sensitive** and **exact prefix**.
- A trace with labels like `"flow: My Bot"` (lowercase) would **NOT** match.
- A trace with `"Flow:My Bot"` (no space after colon) would **NOT** match.
- Only the **first** matching `"Flow: "` label is used — if a trace has multiple flow labels, all but the first are ignored.

---

## 5. `_filter_by_ownership` (KEY METHOD)

### Signature

```python
async def _filter_by_ownership(
    self,
    traces: list[dict],
    allowed_flow_ids: set[UUID],
) -> tuple[list[dict], dict[str, FlowMeta]]
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `traces` | `list[dict]` | Raw trace dicts from LangWatch (NOT yet parsed) |
| `allowed_flow_ids` | `set[UUID]` | Flow UUIDs the caller is permitted to see |

### Processing (step by step)

#### Step 1: Early exit

```python
if not allowed_flow_ids:
    return [], {}
```

If the caller has no allowed flows, return immediately with empty results. **No traces will ever be returned for a user with no flows.**

#### Step 2: Query DB for flow metadata

```python
stmt = (
    select(Flow.id, Flow.name, Flow.user_id, User.username)
    .join(User, Flow.user_id == User.id, isouter=True)
    .where(Flow.id.in_(allowed_flow_ids))
)
result = await self._db_session.exec(stmt)
rows = result.all()
```

- Queries the `Flow` table joined (left outer) to `User`.
- Filters to only flows whose `id` is in `allowed_flow_ids`.
- Returns rows with: `id`, `name`, `user_id`, `username`.

#### Step 3: Build `flow_name_map`

```python
flow_name_map: dict[str, FlowMeta] = {}
```

Iterates over DB rows. For each row, creates a `FlowMeta(flow_id, user_id, username)`.

**Collision handling** (when two flows share the same name):

```python
existing = flow_name_map.get(row.name)
if existing is None:
    flow_name_map[row.name] = meta
else:
    # Prefer the one whose ID is in allowed_flow_ids
    new_allowed = row.id in allowed_flow_ids
    old_allowed = existing.flow_id in allowed_flow_ids
    if new_allowed and not old_allowed:
        flow_name_map[row.name] = meta
    elif new_allowed and old_allowed:
        # Both allowed — prefer most recently created
        if hasattr(row, "created_at") and row.created_at and (
            not hasattr(existing, "created_at")
            or not getattr(existing, "created_at", None)
            or row.created_at > existing.created_at
        ):
            flow_name_map[row.name] = meta
```

**Critical observations about the collision logic:**

1. All rows come from a query filtered by `Flow.id.in_(allowed_flow_ids)`, so `row.id in allowed_flow_ids` is **always True** for every row. The `new_allowed` / `old_allowed` check is therefore **always both True**.
2. The tie-break checks `hasattr(row, "created_at")` — but `row` is a SQLAlchemy Row tuple, not a `FlowMeta` object. Whether `created_at` is available depends on whether it was included in the `select()`. **It was NOT selected** — the select only includes `Flow.id, Flow.name, Flow.user_id, User.username`. So `hasattr(row, "created_at")` likely returns **False**, meaning the tie-break **never fires** and the first row wins arbitrarily.
3. The check `not hasattr(existing, "created_at")` references `existing` which is a `FlowMeta` — `FlowMeta` does **not** have a `created_at` field, so this would always be True. But this branch is only reached if `hasattr(row, "created_at")` is True, which it likely isn't.

**Net effect of collision handling:** When two allowed flows share the same name, the **first one returned by the DB query** wins. The tie-break logic is effectively dead code due to `created_at` not being selected.

#### Step 4: Build `allowed_names`

```python
allowed_names = set(flow_name_map.keys())
```

This is the set of **flow names** (strings, not UUIDs) that the user is allowed to see. It is derived from the DB query results.

#### Step 5: Filter traces

```python
filtered: list[dict] = []
for trace in traces:
    metadata = trace.get("metadata") or {}
    labels: list = metadata.get("labels") or []
    flow_name = next(
        (lbl[6:] for lbl in labels if isinstance(lbl, str) and lbl.startswith("Flow: ")),
        None,
    )
    if flow_name in allowed_names:
        filtered.append(trace)
```

For each trace:
1. Extracts `metadata.labels` (same logic as `_parse_trace`).
2. Finds the first label matching `"Flow: <name>"`.
3. Checks if the extracted `flow_name` is in `allowed_names`.
4. If yes, the trace is included. If no, the trace is **silently dropped**.

### Output

Returns `tuple[list[dict], dict[str, FlowMeta]]`:
- `filtered`: traces whose `flow_name` is in the allowed set
- `flow_name_map`: `dict[str, FlowMeta]` mapping flow name -> DB metadata

### What Happens When a Trace Has NO Labels?

- `labels` defaults to `[]`.
- `flow_name` becomes `None` (the `next()` default).
- `None in allowed_names` evaluates to `False` (since `allowed_names` is a set of strings).
- **The trace is silently dropped.** It does not appear in results.

### What is `unmatched_traces`?

**There is no `unmatched_traces` variable.** The method does not track or report which traces were filtered out. Traces that don't match are simply not added to `filtered`. There is no logging, no counter, no diagnostic output for dropped traces.

### Failure Modes

| Condition | Result |
|-----------|--------|
| `allowed_flow_ids` is empty | Returns `([], {})` immediately |
| Flow was deleted from DB but traces exist in LangWatch | Flow won't appear in DB query -> its name won't be in `allowed_names` -> **all its traces are silently dropped** |
| Flow was renamed in DB but LangWatch traces have old name | Old name not in `allowed_names` -> **traces with old name are silently dropped** |
| Two flows share the same name | Name collision — only one `FlowMeta` stored. All matching traces are counted, but attributed to one flow's metadata |
| Trace has no `"Flow: "` label | `flow_name = None` -> **trace is silently dropped** |
| Trace has label with wrong case (`"flow: "`) | Does not match prefix -> **trace is silently dropped** |
| Trace has label with no space after colon (`"Flow:Bot"`) | Does not match prefix -> **trace is silently dropped** |
| DB query fails | Exception propagates — no traces returned |

### Critical Gap: Name-Based Matching

The entire filtering system relies on **string name matching** between:
- The `Flow.name` column in the database
- The `"Flow: <name>"` label embedded in LangWatch trace metadata

There is **no flow ID** in the LangWatch trace metadata. This means:
- **Renamed flows** lose their historical traces (the old name no longer matches).
- **Duplicate-named flows** have their traces merged/misattributed.
- **Deleted flows** whose names are no longer in the DB have all their traces invisible.

---

## 6. `_aggregate_with_metadata`

### Signature

```python
def _aggregate_with_metadata(
    self,
    traces: list[dict],
    params: UsageQueryParams,
    flow_name_map: dict[str, FlowMeta] | None = None,
) -> UsageResponse
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `traces` | `list[dict]` | Raw trace dicts (already filtered by `_filter_by_ownership`) |
| `params` | `UsageQueryParams` | For date range metadata in response |
| `flow_name_map` | `dict[str, FlowMeta] | None` | Optional DB metadata mapping |

### Processing (step by step)

1. **Parse all traces** via `_parse_trace`:
   ```python
   parsed = [p for t in traces if (p := self._parse_trace(t)) is not None]
   ```
   Malformed traces are silently dropped here.

2. **Group by `flow_name`**:
   ```python
   groups: dict[str | None, list[dict]] = defaultdict(list)
   for p in parsed:
       groups[p["flow_name"]].append(p)
   ```

3. **Build per-flow aggregates** — iterates `groups.items()`:
   - **Skips `flow_name is None`** — traces without a flow label are excluded from aggregation even if they somehow survived filtering.
   - For each named flow:
     - `total_cost` = sum of `cost_usd`
     - `invocation_count` = count of traces
     - `avg_cost` = `total_cost / invocation_count`
   - Looks up `FlowMeta` from `flow_name_map` if available:
     - If found: uses real `flow_id`, `user_id`, `username` from DB.
     - If not found: generates a deterministic UUID via `uuid5(NAMESPACE_DNS, f"langbuilder.flow.{flow_name}")`, sets `owner_user_id = UUID(int=0)`, `owner_username = ""`.
   - Creates a `FlowUsage` object.

4. **Sorts** `flow_usages` by `total_cost_usd` descending.

5. **Builds summary totals**:
   - `total_cost_usd` = sum of all flow costs
   - `total_invocations` = sum of all flow invocation counts
   - `avg_cost_per_invocation_usd` = total / invocations
   - `active_flow_count` = number of unique flows
   - `truncated` = True if `len(traces) >= MAX_PAGES * PAGE_SIZE` (10,000)

6. Returns `UsageResponse(summary=summary, flows=flow_usages)`.

### Output

`UsageResponse` containing:
- `summary`: `UsageSummary` with totals, date range, cache/truncation flags
- `flows`: `list[FlowUsage]` sorted by cost descending

### Failure Modes

| Condition | Result |
|-----------|--------|
| `_parse_trace` returns `None` for a trace | Trace is silently dropped from aggregation |
| Trace has `flow_name = None` after parsing | Trace is explicitly skipped (`if flow_name is None: continue`) |
| `flow_name_map` is None | Placeholder UUIDs used (uuid5-derived) — no real DB data |
| `flow_name` not in `flow_name_map` | Same placeholder behavior — real DB data not found |
| Zero valid traces | Returns response with empty `flows` list, all totals = 0 |

---

## 7. `get_usage_summary`

### Signature

```python
async def get_usage_summary(
    self,
    params: UsageQueryParams,
    allowed_flow_ids: set[UUID],
    api_key: str,
    org_id: str = "default",
    *,
    is_admin: bool = False,
) -> UsageResponse
```

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `params` | `UsageQueryParams` | Date range, sub_view, user_id filter |
| `allowed_flow_ids` | `set[UUID]` | Flow UUIDs the caller may see |
| `api_key` | `str` | Decrypted LangWatch API key |
| `org_id` | `str` | Org identifier for cache key scoping |
| `is_admin` | `bool` | Whether caller is a superuser |

### Processing (step by step)

1. **Build cache key**: `_build_cache_key(params, allowed_flow_ids, org_id, is_admin=is_admin)`.

2. **Cache read** (if Redis available):
   - Attempts `redis.get(cache_key)`.
   - On hit: deserializes via `UsageResponse.model_validate_json()`, sets `summary.cached = True`, computes `cache_age_seconds`, returns immediately.
   - On Redis error: logs warning, proceeds uncached.

3. **Fetch from LangWatch**:
   ```python
   raw_data = await self._fetch_from_langwatch(params, api_key)
   ```
   - On `httpx.TimeoutException`: raises `LangWatchUnavailableError`.
   - On `httpx.TransportError`: raises `LangWatchUnavailableError`.

4. **Filter by ownership**:
   ```python
   filtered, flow_map = await self._filter_by_ownership(raw_data, allowed_flow_ids)
   ```

5. **Aggregate**:
   ```python
   aggregated = self._aggregate_with_metadata(filtered, params, flow_name_map=flow_map)
   ```

6. **Cache write** (if Redis available):
   - Serializes `aggregated.model_dump_json(by_alias=True)`.
   - Stores with TTL = `cache_ttl` (300 seconds / 5 minutes).
   - On Redis error: logs warning, continues.

7. **Returns** `aggregated`.

### Full Pipeline

```
get_usage_summary
  |
  +--> _build_cache_key()
  |
  +--> [Redis cache check]
  |      |-- HIT: return cached UsageResponse
  |      |-- MISS: continue
  |
  +--> _fetch_from_langwatch(params, api_key)
  |      |
  |      +--> _fetch_all_pages(api_key, start_ms, end_ms)
  |             |
  |             +--> POST /api/traces/search (up to 10 pages)
  |
  +--> _filter_by_ownership(raw_traces, allowed_flow_ids)
  |      |
  |      +--> DB query: Flow JOIN User WHERE id IN allowed_flow_ids
  |      +--> Build flow_name_map: {flow_name: FlowMeta}
  |      +--> Build allowed_names: set of flow name strings
  |      +--> Filter traces: keep only where "Flow: <name>" label in allowed_names
  |
  +--> _aggregate_with_metadata(filtered_traces, params, flow_map)
  |      |
  |      +--> _parse_trace() each trace
  |      +--> Group by flow_name
  |      +--> Skip flow_name=None
  |      +--> Sum costs, count invocations
  |      +--> Resolve FlowMeta from flow_map
  |      +--> Build UsageResponse
  |
  +--> [Redis cache write]
  |
  +--> return UsageResponse
```

### Failure Modes

| Condition | Result |
|-----------|--------|
| Redis unavailable | Graceful degradation — all requests hit LangWatch API directly |
| LangWatch timeout/network error | `LangWatchUnavailableError` raised |
| LangWatch auth failure (401/403) | `LangWatchInvalidKeyError` raised (from `_fetch_all_pages`) |
| `allowed_flow_ids` empty | `_filter_by_ownership` returns `([], {})` -> empty response |
| All traces filtered out | Valid but empty `UsageResponse` returned |
| `params.sub_view` is "mcp" | **No special handling** — sub_view only affects cache key, not actual filtering |
| `params.user_id` is set | **No filtering by user_id** — only affects cache key, not actual filtering |

---

## 8. End-to-End Data Flow Diagram

```
LangWatch API                  Usage Service                    Database
     |                              |                              |
     |  <-- POST /api/traces/search |                              |
     |      {startDate, endDate,    |                              |
     |       pageSize, scrollId?}   |                              |
     |  --> {traces: [...],         |                              |
     |       pagination: {scrollId}}|                              |
     |                              |                              |
     |  (up to 10 pages, 10K max)   |                              |
     |                              |                              |
     |        raw_traces (ALL org)  |                              |
     |                              |                              |
     |                              | -- SELECT Flow.id, Flow.name |
     |                              |    Flow.user_id, User.username|
     |                              |    WHERE Flow.id IN (...)  -->|
     |                              |                              |
     |                              | <-- rows: [(id,name,uid,un)] |
     |                              |                              |
     |     flow_name_map built      |                              |
     |     {name: FlowMeta}         |                              |
     |                              |                              |
     |     allowed_names = set of   |                              |
     |     flow name strings        |                              |
     |                              |                              |
     |     For each trace:          |                              |
     |       extract "Flow: <name>" |                              |
     |       from metadata.labels   |                              |
     |       if name in allowed_names -> KEEP                      |
     |       else -> DROP (silent)  |                              |
     |                              |                              |
     |     Parse kept traces        |                              |
     |     Group by flow_name       |                              |
     |     Aggregate costs/counts   |                              |
     |     Attach FlowMeta from DB  |                              |
     |                              |                              |
     |     Return UsageResponse     |                              |
```

---

## 9. Identified Failure Modes & Gaps

### Gap 1: Name-Based Matching (Primary Issue)

The entire trace-to-flow matching system hinges on string equality between `Flow.name` in the DB and the `"Flow: <name>"` label in LangWatch traces. There is **no flow ID** stored in LangWatch metadata.

**Consequence:** Any of the following will cause traces to become invisible:
- Flow renamed in the application (DB name changes, LangWatch labels retain old name)
- Flow deleted from the application (name no longer in DB)
- Label not set at trace-send time (flow_name = None -> always filtered out)
- Label has different casing or formatting

### Gap 2: Silent Dropping with No Diagnostics

There is no `unmatched_traces` tracking. No logging. No counter. When traces are dropped, there is zero visibility into:
- How many traces were dropped
- Why they were dropped (no label? wrong name? flow deleted?)
- Which flow names appeared in traces but weren't in the allowed set

### Gap 3: `params.user_id` and `params.sub_view` Are Not Used for Filtering

These fields exist in `UsageQueryParams` and affect the **cache key** but are **never used for actual data filtering**:
- `user_id` does not filter traces to a specific user's flows
- `sub_view` ("flows" vs "mcp") does not change what data is fetched or how it's filtered

### Gap 4: Collision Tie-Break Is Dead Code

The `_filter_by_ownership` collision handling tries to use `row.created_at` for tie-breaking when two flows share a name, but:
- `created_at` is **not selected** in the SQL query
- `FlowMeta` does **not have** a `created_at` field
- The `hasattr(row, "created_at")` check likely returns False
- Result: first DB row wins arbitrarily

### Gap 5: Truncation Without Warning

If there are more than 10,000 traces in the date range, only the first 10,000 are fetched. The `truncated` flag is set in the response, but:
- No warning is logged server-side
- The client must check `summary.truncated` to know data is incomplete
- There is no indication of *how many* traces were missed

### Gap 6: All-Org Fetch Then Client-Side Filter

Every call fetches **all** traces for the entire LangWatch API key (org) within the date range, regardless of which flows the user is allowed to see. For large orgs with many flows, this means:
- Fetching far more data than needed
- Higher latency and API load
- Hitting the 10,000 trace cap sooner (truncation risk)

The LangWatch API does not appear to support server-side flow/label filtering based on how it's called here.

### Gap 7: Redis Currently Non-Functional

The DI factory (`get_langwatch_service`) has a note:
```python
# NOTE: get_redis_client does not exist in lfx.services.deps — Redis caching is
# currently non-functional. All requests hit the LangWatch API directly.
```

`redis_client` is always `None` in practice, meaning every request hits the LangWatch API with no caching.
