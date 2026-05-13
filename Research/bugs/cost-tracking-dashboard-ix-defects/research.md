---
skill: serious-research
slug: cost-tracking-dashboard-ix-defects
status: done
parent: QA/cost-tracking-dashboard-ix
created: 2026-03-17
classification: Bug
scope: Codebase only
mode: Deep
---

# Cost Tracking Dashboard IX — Defect Investigation

## Summary

Deep investigation of the Cost Tracking Dashboard IX feature revealed **19 bugs** (4 CRASH, 10 LOGIC, 3 INTEGRATION, 2 STYLE) plus **4 navigation defects**. The feature is completely non-functional: every API endpoint crashes before returning data due to two instances of the same root cause — wrapping a bare async generator with `async with`.

Beyond the crash bugs, the investigation uncovered that the Redis caching layer is entirely dead code (the import fails silently), the SQLite migration is incompatible, null dates crash the service, httpx errors propagate as raw 500s, and there's a cross-user data leakage vector via cache key collision.

The navigation placement (Usage link in the AppHeader) violates established codebase patterns where top-level sections navigate via the Account Menu dropdown.

## Background

The Cost Tracking Dashboard IX was implemented as a 41-task, 5-feature project with 670+ tests. The coding report claims 100% completion. However, QA review against the running application revealed critical runtime failures that the test suite did not catch — likely because tests mock the dependency injection layer rather than exercising the real FastAPI DI path.

## Findings

### Category 1: CRASH Bugs (Block All Endpoints)

**BUG-C1: Router `_injectable_db_session` uses `async with` on async generator**
- **File:** `langflow/api/v1/usage/router.py:47-52`
- **Root cause:** `injectable_session_scope()` is a bare async generator (no `@asynccontextmanager`). Wrapping it with `async with` raises `AttributeError`. Every other router imports `DbSession` from `langflow.api.utils` which uses `Depends(injectable_session_scope)` correctly.
- **Fix:** Delete lines 44-57, import `from langflow.api.utils import CurrentActiveUser, DbSession`.

**BUG-C2: Service `_injectable_session` has the same `async with` crash**
- **File:** `langflow/services/langwatch/service.py:108-118`
- **Root cause:** Identical pattern — wraps `injectable_session_scope()` with `async with`. Used by `get_langwatch_service()` at line 916. This means the `LangWatchService` dependency itself crashes before construction.
- **Fix:** Delete `_injectable_session`, have `get_langwatch_service` accept `session: DbSession` from `langflow.api.utils`.

**BUG-C3: Null date crash in `_fetch_from_langwatch`**
- **File:** `langflow/services/langwatch/service.py:260-261`
- **Root cause:** `from_date`/`to_date` default to `None`. Code calls `.timestamp()` on `None`. The `fetch_flow_runs` method handles this correctly (lines 633-638) but `_fetch_from_langwatch` does not.
- **Fix:** Add null checks matching the `fetch_flow_runs` pattern.

**BUG-C4: Unhandled `httpx.HTTPStatusError` in `_fetch_all_pages`**
- **File:** `langflow/services/langwatch/service.py:211`
- **Root cause:** `response.raise_for_status()` raises `httpx.HTTPStatusError` which is not a subclass of `LangWatchError`. The router's `except LangWatchError` doesn't catch it. Raw 500 with traceback.
- **Fix:** Catch `httpx.HTTPStatusError` in `_fetch_all_pages`, wrap in appropriate `LangWatchError` subclass.

### Category 2: LOGIC Bugs

**BUG-L1: Redis caching is entirely dead code**
- **File:** `langflow/services/langwatch/service.py:932`
- **Root cause:** `from lfx.services.deps import get_redis_client` — this function does not exist in `lfx.services.deps`. The `# type: ignore[import]` suppresses the linter, and `except Exception` silently swallows the `ImportError`. `redis_client` is always `None`. The entire cache-aside pattern never executes.
- **Impact:** Every request hits the LangWatch API directly. Bug 8 (Redis KEYS command) is moot.

**BUG-L2: `get_langwatch_service` leaks httpx connections**
- **File:** `langflow/services/langwatch/service.py:915-936`
- **Root cause:** `get_langwatch_service` is a regular function that `return`s, not an async generator that `yield`s. Each request creates a new `LangWatchService` with a new `httpx.AsyncClient` that is never `aclose()`d.
- **Fix:** Convert to async generator with cleanup, or make the httpx client a singleton.

**BUG-L3: `get_usage_summary` has no httpx error handling**
- **File:** `langflow/services/langwatch/service.py:555`
- **Root cause:** Calls `_fetch_from_langwatch` without try/except for network errors. Compare with `fetch_flow_runs` (lines 641-652) which wraps its call properly.

**BUG-L4: Cache key collision leaks cross-user data (SECURITY)**
- **File:** `langflow/services/langwatch/service.py:496-501`
- **Root cause:** Admin with zero flows and non-admin with zero flows both get cache key scope `"all"`. A cached admin response can be served to a non-admin user.
- **Severity:** HIGH security concern per Security Reviewer.

**BUG-L5: Flow name collision in `_filter_by_ownership`**
- **File:** `langflow/services/langwatch/service.py:365`
- **Root cause:** `flow_name_map` keyed by `flow.name` but names aren't unique. Two users with "My Chatbot" flow — one overwrites the other.

**BUG-L6: Duplicate ownership check in `fetch_flow_runs`**
- **Files:** `router.py:222-246`, `service.py:655-672`
- **Root cause:** Router checks ownership (raises 403), then service checks again (returns empty). Extra DB query, inconsistent error behavior.

**BUG-L7: Dead `get_flow_runs` stub raises `NotImplementedError`**
- **File:** `langflow/services/langwatch/service.py:574-584`

**BUG-L8: `datetime.utcnow` deprecated + naive/aware tz mixing**
- **File:** `langflow/services/database/models/global_settings.py:21-22`
- **Root cause:** Model defaults use `datetime.utcnow` (naive), but `save_key` uses `datetime.now(tz=timezone.utc)` (aware). Mixing can raise `TypeError`.

**BUG-L9: Migration uses `NOW()` incompatible with SQLite**
- **File:** `langflow/alembic/versions/773db17e6029:31,37`
- **Root cause:** `sa.text("NOW()")` is PostgreSQL-only. SQLite needs `sa.func.now()` or `CURRENT_TIMESTAMP`.
- **Impact:** Blocks ALL SQLite deployments.

**BUG-L10: `org_id` set to `current_user.id`**
- **File:** `langflow/api/v1/usage/router.py:194`
- **Impact:** Cache scoping uses user ID instead of org ID, reducing cache hit rate.

### Category 3: INTEGRATION Bugs

**BUG-I1: `DateRange.from_` alias fragility**
- **Files:** `schemas.py:34`, `service.py:565`
- **Root cause:** `model_dump_json()` uses field name `from_` not alias `from`. Cache serialization differs from API response serialization.

**BUG-I2: Frontend throws raw JSON, not Error objects**
- **File:** `src/frontend/src/services/LangWatchService.ts:25,44,55,73`
- **Root cause:** `throw await response.json()` — UsagePage checks `error instanceof Error` which is always false. Users always see generic "An error occurred".

**BUG-I3: Frontend error handling in UsagePage**
- **File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`
- **Root cause:** Error display logic doesn't handle structured error responses from the backend.

### Category 4: Navigation Defects

**NAV-1:** Usage link is a bare `<Link>` in AppHeader — should be in Account Menu dropdown like Settings.
**NAV-2:** Uses `<Link>` instead of `useCustomNavigate()` hook.
**NAV-3:** No feature flag (unlike Knowledge/My Files).
**NAV-4:** UsagePage doesn't use `PageLayout` wrapper (unlike Settings).

### Category 5: STYLE Issues

**STY-1:** Mixed `exec`/`execute` on same session type in service.py.
**STY-2:** Five bare `except Exception` blocks silently swallow errors.

## Sync Pairs Identified

| Function A | Function B | Must agree on |
|-----------|-----------|---------------|
| `_fetch_from_langwatch` null handling | `fetch_flow_runs` null handling | How None dates are converted to timestamps |
| Router ownership check (403) | Service ownership check (empty response) | Authorization failure behavior |
| `model_dump_json()` serialization | FastAPI `response_model` serialization | Field alias usage (`from` vs `from_`) |
| `LangWatchService.ts` error throwing | `UsagePage.tsx` error display | Error object shape |
| `global_settings.py` datetime defaults | `service.py save_key` datetime usage | Timezone awareness |

## Recommendations

### Priority 1 — Fix DI crashes (BUG-C1, BUG-C2)
Replace both broken `_injectable_db_session` / `_injectable_session` with canonical `DbSession` import from `langflow.api.utils`. This also fixes the dual-session issue. Single fix unblocks all 4 endpoints.

### Priority 2 — Fix null date crash (BUG-C3)
Add null handling in `_fetch_from_langwatch` matching `fetch_flow_runs` pattern.

### Priority 3 — Fix httpx error handling (BUG-C4, BUG-L3)
Catch `httpx.HTTPStatusError` and `httpx.TransportError` in both code paths. Wrap in `LangWatchError` subclasses.

### Priority 4 — Fix SQLite migration (BUG-L9)
Replace `sa.text("NOW()")` with `sa.func.now()`.

### Priority 5 — Fix security: cache key collision (BUG-L4)
Include user identity in cache key when `allowed_flow_ids` is empty. Short-circuit to empty response for non-admins with zero flows.

### Priority 6 — Fix frontend error display (BUG-I2, BUG-I3)
Throw `new Error()` in LangWatchService.ts or update UsagePage.tsx to handle structured errors.

### Priority 7 — Fix connection leak (BUG-L2)
Convert `get_langwatch_service` to async generator or make httpx client a singleton.

### Priority 8 — Fix Redis import (BUG-L1)
Implement `get_redis_client` in lfx deps or use correct import path. Currently entire cache layer is dead.

### Priority 9 — Navigation fixes (NAV-1 through NAV-4)
Move Usage to Account Menu dropdown, add feature flag, use PageLayout.

### Lower priority
BUG-L5 (flow name collision), BUG-L6 (duplicate ownership), BUG-L7 (dead code), BUG-L8 (datetime), BUG-L10 (org_id), BUG-I1 (alias), STY-1, STY-2.

## References

All file paths relative to codebase root:
`/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/`

| File | Key lines | Role |
|------|-----------|------|
| `src/backend/base/langflow/api/v1/usage/router.py` | 47-52 (crash), 194 (org_id) | Usage API endpoints |
| `src/backend/base/langflow/services/langwatch/service.py` | 108-118 (crash), 260-261 (null), 211 (httpx), 496-501 (cache), 915-936 (leak) | LangWatch service |
| `src/backend/base/langflow/api/utils/core.py` | 40 | Canonical DbSession definition |
| `src/lfx/src/lfx/services/deps.py` | 149-151, 154-192 | Session dependency definitions |
| `src/backend/base/langflow/services/langwatch/schemas.py` | 34 | DateRange alias |
| `src/backend/base/langflow/services/database/models/global_settings.py` | 21-22 | Datetime defaults |
| `src/backend/base/langflow/alembic/versions/773db17e6029_...py` | 31, 37 | Migration NOW() |
| `src/frontend/src/services/LangWatchService.ts` | 25, 44, 55, 73 | Error throwing |
| `src/frontend/src/pages/UsagePage/UsagePage.tsx` | error display | Error handling |
| `src/frontend/src/components/core/appHeaderComponent/index.tsx` | 86-92 | Usage link (nav defect) |
| `src/frontend/src/components/core/appHeaderComponent/components/AccountMenu/index.tsx` | 87-98 | Settings nav (correct pattern) |

### Thread files
- `thread-1-navigation-architecture.md` — Navigation inventory and patterns
- `thread-2-db-session-pattern.md` — DB session dependency analysis across all routers
- `thread-3-usage-router-audit.md` — Full audit of 15 bugs

### Persona reviews
- **Senior Engineer** — Found 4 additional bugs (service crash, dead Redis, connection leak, flow name collision). Corrected severity classifications.
- **Security Reviewer** — Confirmed cache key collision as HIGH security issue. Validated Fernet encryption as sound. No auth bypass found.
