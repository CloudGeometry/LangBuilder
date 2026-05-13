---
skill: serious-plan
slug: fix-service-cleanup
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 06: Service Cleanup (Connection Leak, Logic Bugs, Dead Code, Style)

**Bugs:** BUG-L2, BUG-L5, BUG-L6, BUG-L7, STY-1, STY-2
**Priority:** 6 (correctness + cleanup)
**Depends on:** Plans 01, 02 (DI crash and null-date fixes must land first)
**File:** `src/backend/base/langflow/services/langwatch/service.py`

---

## Task 1: Fix httpx connection leak (BUG-L2)

**Problem:** `get_langwatch_service` (line 915) is a regular function that `return`s a `LangWatchService`. Each call creates a new `httpx.AsyncClient` (line 136) that is never closed. Connections leak on every request.

**Fix:** Convert `get_langwatch_service` to an async generator that `yield`s the service and closes the client in a `finally` block.

```python
# service.py ~915-936 — replace the function with:
async def get_langwatch_service(
    session: AsyncSession = Depends(_injectable_session),
) -> AsyncGenerator[LangWatchService, None]:
    redis_client = None
    try:
        from lfx.services.deps import get_redis_client  # type: ignore[import]
        redis_client = get_redis_client()
    except Exception:  # noqa: BLE001, S110
        pass
    svc = LangWatchService(db_session=session, redis=redis_client)
    try:
        yield svc
    finally:
        await svc.aclose()
```

Add `AsyncGenerator` to the imports at the top of the file:

```python
from collections.abc import AsyncGenerator
```

> **AMENDMENT (review verdict):** Use `collections.abc.AsyncGenerator`, not `typing.AsyncGenerator` (which is deprecated in Python 3.9+). This import is required for the return type annotation `AsyncGenerator[LangWatchService, None]` on the amended `get_langwatch_service`.

**Verify:** `aclose()` already exists (added in F2-T2). Confirm it calls `await self._client.aclose()`.

---

## Task 2: Fix flow name collision (BUG-L5)

**Problem:** `_filter_by_ownership` (line 362-369) builds `flow_name_map` keyed by `flow.name`. Flow names are not unique — two users can both have a flow named "My Chatbot". One entry overwrites the other, causing incorrect ownership attribution.

> **AMENDMENT (review verdict):** The original plan proposed re-keying by `flow.id`. This is **UNSAFE** — LangWatch traces only contain flow *names* in labels (e.g., `"Flow: My Chatbot"`), not flow IDs. Changing to `flow_id` keying would break trace matching entirely. The downstream consumer `_aggregate_with_metadata` (line 435) does `flow_name_map.get(flow_name)`, confirming name-based keying must stay.

**Fix:** Keep `flow_name_map` keyed by name, but handle collisions when building the map. When a duplicate name is encountered:

1. If only one of the two flows has its ID in `allowed_flow_ids`, prefer that one.
2. If both are allowed (admin view), pick deterministically by most recent `created_at`.
3. Add a code comment noting that the LangWatch label format cannot disambiguate flows with truly identical names across users.

```python
# service.py ~362-371 — replace the map-building loop with:
flow_name_map: dict[str, FlowMeta] = {}
for row in rows:
    meta = FlowMeta(
        flow_id=row.id,
        user_id=row.user_id or UUID(int=0),
        username=row.username or "",
    )
    existing = flow_name_map.get(row.name)
    if existing is None:
        flow_name_map[row.name] = meta
    else:
        # Collision: two flows share a name.
        # Prefer the one whose ID is in allowed_flow_ids.
        new_allowed = row.id in allowed_flow_ids
        old_allowed = existing.flow_id in allowed_flow_ids
        if new_allowed and not old_allowed:
            flow_name_map[row.name] = meta
        elif new_allowed and old_allowed:
            # Both allowed (admin view) — prefer most recently created.
            # NOTE: LangWatch label format cannot disambiguate flows
            # with identical names; this is a best-effort heuristic.
            if row.created_at and (
                not hasattr(existing, "created_at")
                or row.created_at > existing.created_at
            ):
                flow_name_map[row.name] = meta
allowed_names = set(flow_name_map.keys())
```

Do **not** rename `flow_name_map` or change downstream consumers — `_aggregate_with_metadata` and the trace-filtering loop (line 374+) expect name-keyed access and must remain unchanged.

---

## Task 3: Remove duplicate ownership check (BUG-L6)

**Problem:** `fetch_flow_runs` (lines 654-672) performs an ownership check (query DB for flow owner, compare to requesting user). But the router at `router.py:222-246` already performs this same check and raises 403. The service-level check is redundant, adds an extra DB query, and returns an empty response instead of an error — inconsistent with the router's 403 behavior.

**Fix:** Delete lines 654-672 from `service.py`. The router's ownership check is the authoritative one.

```python
# service.py ~654-672 — DELETE this block:
#   # Ownership check: verify the requesting user owns this flow (or is admin)
#   if not is_admin:
#       from sqlmodel import select
#       ...
#       if flow_owner_id != requesting_user_id:
#           return FlowRunsResponse(...)
```

Remove the `is_admin` and `requesting_user_id` parameters from `fetch_flow_runs` if they are only used by this deleted block. Update the router call site accordingly.

> **AMENDMENT (review verdict):** Update the following tests after removing the ownership check:
> - `test_langwatch_flow_runs.py` — update tests for service-level ownership (assertions that expect empty responses for non-owners should be deleted or changed to verify the router handles 403 instead).
> - `test_flow_runs_endpoint.py` — update assertions on the `is_admin` kwarg passed to `fetch_flow_runs` (if the parameter is removed, the test mocks/call-site assertions must match).
> - `test_usage_security.py` — update ownership tests that verify the service-level check; these should now assert the router-level 403 behavior instead.

---

## Task 4: Remove dead code (BUG-L7)

**Problem:** `get_flow_runs` (lines 574-584) is a sync stub that raises `NotImplementedError`. The async `fetch_flow_runs` (line 586) is the real implementation. The stub is never called.

**Fix:** Delete lines 574-584.

> **AMENDMENT (review verdict):** Delete or update tests in `test_langwatch_service_skeleton.py` that reference the sync `get_flow_runs` stub. Any test that calls or mocks `get_flow_runs` (the sync version) should be removed since the method no longer exists.

---

## Task 5: Fix style issues (STY-1, STY-2)

**STY-1:** Mixed `exec` / `execute` usage on the same session type. Audit all `self._db_session.exec(` and `self._db_session.execute(` calls. Standardize on `exec` (the SQLModel convention) for all `select()` queries.

> **AMENDMENT (review verdict):** Do **not** change line 752. The `execute` + `scalar_one_or_none()` pattern at line 752 is an SQLAlchemy-specific accessor that is NOT compatible with SQLModel's `exec`. Leave it as-is. Only standardize the other `execute` instances where the result accessor pattern (e.g., `.scalars().all()`, `.all()`) is compatible with `exec`.

**STY-2:** Five bare `except Exception` blocks silently swallow errors (lines ~567, 908, 934, and others). For each:
- If the exception is expected (e.g., Redis unavailable), narrow to the specific type (`redis.RedisError`, `ImportError`).
- If narrowing is not feasible, keep `except Exception` but ensure logging at `warning` or `debug` level (some already log, verify all do).

---

## Task 6: Verify

1. Start the backend and hit `/api/v1/usage/summary` and `/api/v1/usage/flow-runs/{id}`.
2. Confirm no `ResourceWarning: unclosed` or httpx connection warnings in logs (validates Task 1).
3. Create two flows with the same name under different users. Confirm usage summary attributes traces to the correct owner (validates Task 2).
4. Confirm non-admin accessing another user's flow gets 403 from the router, not an empty response (validates Task 3).
5. Confirm `get_flow_runs` no longer exists as an attribute (validates Task 4).
6. Grep for bare `except Exception` — confirm count is reduced and remaining ones have logging (validates Task 5).
