---
skill: serious-research
slug: cost-tracking-dashboard-ix-defects
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
thread: 3
---

# Thread 3: Usage Router Full Audit

**Investigator:** Thread 3 Agent
**Scope:** Full audit of the usage router, LangWatchService, schemas, migrations, and frontend integration
**Files Audited:**

| Layer | Files |
|-------|-------|
| Router | `src/backend/base/langflow/api/v1/usage/router.py`, `__init__.py` |
| Service | `src/backend/base/langflow/services/langwatch/service.py` |
| Schemas | `src/backend/base/langflow/services/langwatch/schemas.py` |
| Exceptions | `src/backend/base/langflow/services/langwatch/exceptions.py` |
| Model | `src/backend/base/langflow/services/database/models/global_settings.py` |
| Migration | `src/backend/base/langflow/alembic/versions/773db17e6029_add_global_settings_table.py` |
| API router | `src/backend/base/langflow/api/router.py` |
| Frontend svc | `src/frontend/src/services/LangWatchService.ts` |
| Frontend page | `src/frontend/src/pages/UsagePage/UsagePage.tsx` |
| Frontend hooks | `src/frontend/src/pages/UsagePage/hooks/useGetUsageSummary.ts`, `useGetFlowRuns.ts`, `useGetKeyStatus.ts` |
| Frontend types | `src/frontend/src/types/usage.ts` |
| Settings form | `src/frontend/src/pages/SettingsPage/LangWatchKeyForm.tsx` |
| Settings page | `src/frontend/src/pages/SettingsPage/pages/GeneralPage/index.tsx` |

---

## Bug Summary

| # | Severity | Category | Title | File | Lines |
|---|----------|----------|-------|------|-------|
| 1 | **CRASH** | Backend | `_fetch_from_langwatch` crashes on null dates | service.py | 260-261 |
| 2 | **CRASH** | Backend | `_fetch_all_pages` unhandled `HTTPStatusError` | service.py | 211 |
| 3 | **CRASH** | Backend | `get_usage_summary` unhandled httpx errors propagate as 500 | service.py | 555 |
| 4 | **LOGIC** | Backend | Dual session: router and service use independent DB sessions | router.py + service.py | 47-52, 108-118 |
| 5 | **LOGIC** | Backend | `_build_cache_key` conflates admin-all with no-flows-user | service.py | 496-501 |
| 6 | **LOGIC** | Backend | Duplicate ownership check in `fetch_flow_runs` | router.py + service.py | 222-246, 655-672 |
| 7 | **LOGIC** | Backend | Dead code: `get_flow_runs` (sync) method raises `NotImplementedError` | service.py | 574-584 |
| 8 | **LOGIC** | Backend | `invalidate_cache` uses `KEYS` command (O(n), blocks Redis) | service.py | 904 |
| 9 | **LOGIC** | Backend | `datetime.utcnow` deprecated in Python 3.12+ | global_settings.py | 21-22 |
| 10 | **LOGIC** | Backend | Migration uses `NOW()` incompatible with SQLite | migration 773db17e6029 | 31, 37 |
| 11 | **LOGIC** | Backend | `org_id` is set to `current_user.id` (not an org ID) | router.py | 194 |
| 12 | **INTEGRATION** | Frontend/Backend | `DateRange.from_` serialization alias only works via FastAPI, not in cache round-trip | schemas.py + service.py | 34, 565 |
| 13 | **INTEGRATION** | Frontend | Error thrown by `response.json()` may not be a valid Error object | LangWatchService.ts | 25, 44, 55, 73 |
| 14 | **STYLE** | Backend | `exec` vs `execute` mixed inconsistently on same session | service.py | 359, 661, 752 |
| 15 | **STYLE** | Backend | Bare `except Exception` catches too broadly in 5 places | service.py | various |

---

## Detailed Findings

### BUG 1 — CRASH: `_fetch_from_langwatch` crashes when `from_date` or `to_date` is `None`

**File:** `src/backend/base/langflow/services/langwatch/service.py`, lines 228-267
**Severity:** CRASH

When `UsageQueryParams.from_date` is `None` (the default), the code falls through to:

```python
# Line 253
from_dt = from_date  # from_date is None

# Line 260
start_ms = int(from_dt.timestamp() * 1000)  # AttributeError: 'NoneType' has no attribute 'timestamp'
```

The `from_date` and `to_date` fields on `UsageQueryParams` are typed as `date | None` and default to `None`. The `_fetch_from_langwatch` method only handles conversion from `date` to `datetime` but never handles `None`. It passes `None` through, then crashes when calling `.timestamp()` on it.

**Note:** `fetch_flow_runs` (line 633-638) correctly handles this case with `if from_datetime else 0` and `if to_datetime else int(datetime.now(...).timestamp() * 1000)`. The fix was applied in one place but not the other.

**Impact:** Any request to `GET /api/v1/usage/` without `from_date` or `to_date` query params will return a 500.

---

### BUG 2 — CRASH: `_fetch_all_pages` unhandled `httpx.HTTPStatusError`

**File:** `src/backend/base/langflow/services/langwatch/service.py`, line 211
**Severity:** CRASH

```python
response.raise_for_status()
```

This raises `httpx.HTTPStatusError` for 4xx/5xx responses from LangWatch. But `_fetch_all_pages` does not catch it, `_fetch_from_langwatch` does not catch it, and `get_usage_summary` does not catch it either.

The error propagates to the router:

```python
# router.py line 198
except LangWatchError as exc:
    _raise_langwatch_http_error(exc)
```

But `httpx.HTTPStatusError` is NOT a subclass of `LangWatchError`, so it escapes the handler and becomes an unhandled 500 with a raw httpx traceback.

**Impact:** If LangWatch returns a 401, 403, 429, or 5xx response during trace fetch, the user sees a raw 500 error instead of a structured error response.

---

### BUG 3 — CRASH: `get_usage_summary` has no httpx error handling

**File:** `src/backend/base/langflow/services/langwatch/service.py`, lines 534-570
**Severity:** CRASH

The `get_usage_summary` method calls `_fetch_from_langwatch` (line 555) without any try/except for network errors. Compare with `fetch_flow_runs` (line 641-652) which wraps its `_fetch_all_pages` call in `try/except httpx.TimeoutException, httpx.TransportError`.

`get_usage_summary` relies on the caller (the router) catching `LangWatchError`, but raw httpx exceptions are not `LangWatchError` subclasses.

**Impact:** Network errors, timeouts, and connection failures during the usage summary endpoint will surface as unhandled 500s.

---

### BUG 4 — LOGIC: Dual session problem (router vs service use independent sessions)

**File:** `router.py` lines 47-55 and `service.py` lines 108-118
**Severity:** LOGIC

The router defines its own session dependency:

```python
# router.py line 47
async def _injectable_db_session() -> AsyncSession:
    from lfx.services.deps import injectable_session_scope
    async with injectable_session_scope() as session:
        yield session
```

The service defines a separate one:

```python
# service.py line 108
async def _injectable_session():
    from lfx.services.deps import injectable_session_scope
    async with injectable_session_scope() as session:
        yield session
```

Each call to `injectable_session_scope()` creates a new, independent session. When endpoints like `get_usage_summary` inject both `db: DbSession` AND `langwatch: LangWatchDep`, they operate on two different database sessions.

**Impact:** Data written through one session is not visible to the other within the same request. If `save_key` commits via the service session, but another part of the request reads via the router session, it may see stale data. This also means the `get_usage_summary` endpoint is holding two database connections simultaneously per request.

---

### BUG 5 — LOGIC: `_build_cache_key` conflates admin-see-all with user-has-no-flows

**File:** `src/backend/base/langflow/services/langwatch/service.py`, lines 496-501
**Severity:** LOGIC

```python
if params.user_id:
    user_scope = str(params.user_id)
elif len(allowed_flow_ids) == 0:
    user_scope = "all"
else:
    user_scope = "user"
```

When an admin queries without a `user_id` filter, the router passes `effective_user_id = None` to `_get_flow_ids_for_user`, which returns ALL flow IDs. If there are zero flows in the system, `allowed_flow_ids` is an empty set, so the cache key scope becomes `"all"`.

But a non-admin user who happens to have zero flows will also produce `allowed_flow_ids = set()`, leading to the same `"all"` scope. These two users would share the same cache key despite having fundamentally different access permissions.

**Impact:** In a multi-user deployment where some users have no flows, cached data could leak between users with different permission levels. Edge case but a security concern.

---

### BUG 6 — LOGIC: Duplicate ownership check in `fetch_flow_runs`

**File:** `router.py` lines 222-246, `service.py` lines 655-672
**Severity:** LOGIC

The router's `get_flow_runs` endpoint already performs a full ownership check:

```python
# router.py lines 239-246
if not current_user.is_superuser and flow_owner_id != current_user.id:
    raise HTTPException(status_code=403, ...)
```

Then the `LangWatchService.fetch_flow_runs` method performs the SAME ownership check again:

```python
# service.py lines 655-672
if not is_admin:
    stmt = select(Flow.id, Flow.user_id).where(Flow.id == flow_id)
    result = await self._db_session.exec(stmt)
    ...
    if flow_owner_id != requesting_user_id:
        return FlowRunsResponse(...)  # silently returns empty
```

This is wasteful (extra DB query) and the error behavior is inconsistent: the router raises 403, but the service silently returns an empty response. If the service check ever executes (it shouldn't since the router already blocked), the user would get a 200 with empty data instead of a 403.

**Impact:** Extra unnecessary DB query per request. Inconsistent error behavior if the double-check path is ever reached.

---

### BUG 7 — LOGIC: Dead `get_flow_runs` (sync) method raises `NotImplementedError`

**File:** `src/backend/base/langflow/services/langwatch/service.py`, lines 574-584
**Severity:** LOGIC

```python
def get_flow_runs(self, flow_id, query) -> FlowRunsResponse:
    msg = "Implemented in F2-T9"
    raise NotImplementedError(msg)
```

This synchronous stub is dead code — the router calls `fetch_flow_runs` (the async method). However, its presence is confusing and violates the interface cleanliness. If anyone calls the wrong method, they get a `NotImplementedError` at runtime.

**Impact:** Dead code, potential confusion for developers.

---

### BUG 8 — LOGIC: `invalidate_cache` uses Redis `KEYS` command

**File:** `src/backend/base/langflow/services/langwatch/service.py`, line 904
**Severity:** LOGIC

```python
keys = await self.redis.keys("usage:*")
```

The Redis `KEYS` command is O(n) across ALL keys in the database and blocks the Redis server while executing. The Redis documentation explicitly warns: "Don't use KEYS in your regular application code."

Should use `SCAN` with an iterator pattern instead, or maintain a set of known cache keys.

**Impact:** On a Redis instance with many keys, this will cause latency spikes for ALL Redis clients whenever a LangWatch key is saved.

---

### BUG 9 — LOGIC: `datetime.utcnow` deprecated in Python 3.12+

**File:** `src/backend/base/langflow/services/database/models/global_settings.py`, lines 21-22
**Severity:** LOGIC

```python
created_at: datetime = Field(default_factory=datetime.utcnow)
updated_at: datetime = Field(default_factory=datetime.utcnow)
```

`datetime.utcnow()` is deprecated since Python 3.12 (PEP 768). It returns a naive datetime (no timezone info), which can cause timezone-related bugs when compared with timezone-aware datetimes (like those created in `save_key` with `datetime.now(tz=timezone.utc)` at service.py line 773).

The `save_key` method sets `existing.updated_at = now` using `datetime.now(tz=timezone.utc)` (timezone-aware), but the model default uses `datetime.utcnow` (timezone-naive). Mixing aware and naive datetimes will raise `TypeError` in comparisons.

**Impact:** Inconsistent timezone handling. Deprecation warning noise. Potential `TypeError` in datetime comparisons.

---

### BUG 10 — LOGIC: Migration uses `NOW()` which is incompatible with SQLite

**File:** `src/backend/base/langflow/alembic/versions/773db17e6029_add_global_settings_table.py`, lines 31, 37
**Severity:** LOGIC

```python
server_default=sa.text("NOW()"),
```

`NOW()` is a PostgreSQL function. SQLite does not support `NOW()`. The codebase supports SQLite as a database backend (confirmed by `src/backend/base/langflow/services/database/service.py` lines 117-118 handling `sqlite` driver).

A cross-database compatible default would be `sa.text("(CURRENT_TIMESTAMP)")` or `sa.func.now()`.

**Impact:** The migration will fail when run against a SQLite database, preventing the usage feature from working in SQLite-based deployments (including local development).

---

### BUG 11 — LOGIC: `org_id` is set to `current_user.id`, not an actual org ID

**File:** `src/backend/base/langflow/api/v1/usage/router.py`, line 194
**Severity:** LOGIC

```python
org_id = str(current_user.id)
```

The `org_id` is used as a cache key scope component. Setting it to the current user's ID means every user gets their own cache namespace, defeating the purpose of shared org-level caching. If User A and User B are both admins requesting the same org-wide data, they'll each trigger a separate LangWatch API call and get separate cache entries.

**Impact:** Cache hit rate is artificially low. Each user triggers a separate API call even when they'd see the same data. Cache keys include user IDs which undermines the "org-scoped" cache design.

---

### BUG 12 — INTEGRATION: `DateRange.from_` serialization differs between FastAPI and cache

**File:** `schemas.py` line 34, `service.py` line 565
**Severity:** INTEGRATION

```python
# schemas.py
class DateRange(BaseModel):
    from_: date | None = Field(None, alias="from")
    model_config = {"populate_by_name": True}
```

FastAPI serializes response models using `by_alias=True` by default, so the JSON response contains `"from"` (correct).

But the cache write on service.py line 565:
```python
aggregated.model_dump_json()
```

Uses `by_alias=False` by default (Pydantic v2 default), so the cached JSON contains `"from_"` (the field name) instead of `"from"` (the alias).

When the cached value is deserialized with `model_validate_json()`, it works because `populate_by_name=True` accepts both `"from_"` and `"from"`. But if anything downstream caches the JSON string and sends it directly to the frontend (or logs it), the field name will be `"from_"` instead of `"from"`.

More critically, the frontend TypeScript type expects `date_range.from` (line 19 of `usage.ts`), not `date_range.from_`. If the cache serialization is ever sent directly without going through FastAPI's response_model serialization, the frontend will fail to read the `from` field.

**Impact:** Currently mitigated by FastAPI re-serializing on output, but fragile. Cache debugging will show the wrong field name.

---

### BUG 13 — INTEGRATION: Frontend error handling throws parsed JSON, not Error objects

**File:** `src/frontend/src/services/LangWatchService.ts`, lines 25, 44, 55, 73
**Severity:** INTEGRATION

```typescript
if (!response.ok) throw await response.json();
```

This throws a plain object (the parsed JSON error response), not an `Error` instance. In the `UsagePage.tsx` error display:

```tsx
{error instanceof Error ? error.message : "An error occurred"}
```

Since the thrown object is NOT an `Error` instance, the `instanceof Error` check will ALWAYS be false, and the user will always see the generic "An error occurred" message instead of the actual error detail from the backend.

The `LangWatchKeyForm.tsx` handles this better with its `getErrorMessage` helper that checks for `detail.code`, but `UsagePage.tsx` does not use this approach.

**Impact:** Users see a generic "An error occurred" message instead of actionable error details like "LangWatch API key not configured" or "LangWatch is temporarily unavailable."

---

### BUG 14 — STYLE: `exec` vs `execute` mixed inconsistently

**File:** `src/backend/base/langflow/services/langwatch/service.py`
**Severity:** STYLE

- Line 359: `await self._db_session.exec(stmt)` — SQLModel's `exec` method
- Line 661: `await self._db_session.exec(stmt)` — SQLModel's `exec` method
- Line 752: `await self._db_session.execute(...)` — SQLAlchemy's `execute` method

Both work on `sqlmodel.ext.asyncio.session.AsyncSession`, but they return different result types. `exec` returns SQLModel-typed results with attribute access (`row.name`), while `execute` returns SQLAlchemy `Result` objects. The `_get_setting` method (line 752) correctly uses `execute` + `scalar_one_or_none()`, but the inconsistency makes the code harder to maintain.

**Impact:** No runtime issue, but inconsistent API usage makes the code harder to reason about.

---

### BUG 15 — STYLE: Bare `except Exception` in multiple places

**File:** `src/backend/base/langflow/services/langwatch/service.py`
**Severity:** STYLE

Five separate `except Exception` blocks (lines 548, 551, 567, 908, 934) catch ALL exceptions including programming errors like `AttributeError`, `TypeError`, etc. While the `# noqa: BLE001` comments acknowledge this, swallowing all exceptions makes debugging significantly harder.

Most of these are around Redis operations where the intent is graceful degradation, but catching `Exception` also masks bugs in the cache key building logic, serialization errors, etc.

**Impact:** Bugs in cache-related code paths will be silently swallowed and logged at WARNING level rather than failing fast.

---

## Additional Observations (Not Bugs)

### Router Registration: CONFIRMED CORRECT

The usage router is correctly registered in `src/backend/base/langflow/api/router.py` at line 27 and line 64:
```python
from langflow.api.v1.usage.router import router as usage_router
router_v1.include_router(usage_router)
```

The router prefix is `/usage` (router.py line 41), under `/v1` (router.py line 34), under `/api` (router.py line 82). Full paths: `/api/v1/usage/...`. The frontend uses `BASE_URL_API` which is `/api/v1/` — paths match correctly.

### Migration: CONFIRMED PRESENT

Migration `773db17e6029_add_global_settings_table.py` exists and creates the table with correct columns matching the model. However, the `NOW()` SQLite incompatibility (Bug 10) may prevent it from running.

### GlobalSettings Model: CONFIRMED REGISTERED

The model is imported in `src/backend/base/langflow/services/database/models/__init__.py` (line 6), so Alembic will detect it for autogenerate.

### Settings Page Integration: CONFIRMED CORRECT

`LangWatchKeyForm.tsx` is imported and rendered in `GeneralPage/index.tsx` (line 28, line 179). It's gated behind `isAdmin` (line 167), matching the backend's `CurrentSuperUser` requirement.

### Frontend Service-to-Backend URL Mapping: CONFIRMED CORRECT

| Frontend URL | Backend Route |
|-------------|---------------|
| `${BASE_URL_API}usage/` | `GET /api/v1/usage/` |
| `${BASE_URL_API}usage/${flowId}/runs` | `GET /api/v1/usage/{flow_id}/runs` |
| `${BASE_URL_API}usage/settings/langwatch-key/status` | `GET /api/v1/usage/settings/langwatch-key/status` |
| `${BASE_URL_API}usage/settings/langwatch-key` (POST) | `POST /api/v1/usage/settings/langwatch-key` |

### Frontend TypeScript Types: CONFIRMED MATCH BACKEND

The `src/frontend/src/types/usage.ts` types match the Pydantic response models in `schemas.py`. UUIDs are represented as strings on the frontend side, which is correct since JSON serialization converts UUIDs to strings.

---

## Priority Ranking for Fixes

1. **BUG 1** (CRASH) — Null date crash. Blocks all usage without explicit dates.
2. **BUG 2 + 3** (CRASH) — Unhandled httpx errors. Any LangWatch API failure = 500.
3. **BUG 10** (LOGIC) — SQLite migration failure. Blocks local dev and SQLite deployments.
4. **BUG 4** (LOGIC) — Dual session. Root cause of data consistency issues.
5. **BUG 13** (INTEGRATION) — Frontend error display always generic.
6. **BUG 5** (LOGIC) — Cache key collision between admin and no-flows users.
7. **BUG 11** (LOGIC) — org_id misuse reduces cache effectiveness.
8. **BUG 12** (INTEGRATION) — DateRange alias fragility.
9. **BUG 9** (LOGIC) — datetime.utcnow deprecation and tz mixing.
10. **BUG 8** (LOGIC) — Redis KEYS command performance.
11. **BUG 6** (LOGIC) — Duplicate ownership check.
12. **BUG 7** (LOGIC) — Dead code.
13. **BUG 14 + 15** (STYLE) — Consistency issues.
