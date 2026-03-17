---
skill: serious-plan
slug: fix-security-and-cache
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 04 — Fix Security & Cache (BUG-L4, BUG-L1, BUG-L10, BUG-I1)

**Priority:** 4 (security + cache correctness)
**Depends on:** Plan 01 (DI crash fixes must land first so endpoints are reachable)

**Codebase root:** `/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/`

---

## Task 0 — Review current `_build_cache_key` logic

**Goal:** Understand the existing cache key construction before modifying it.
**File:** `src/backend/base/langflow/services/langwatch/service.py` lines 477-507

Current logic at lines 496-501:
- `params.user_id` set → scope = that user's UUID string
- `len(allowed_flow_ids) == 0` → scope = `"all"`
- else → scope = `"user"`

**Problem (BUG-L4):** An admin with zero `allowed_flow_ids` (meaning "show everything") and a non-admin with zero `allowed_flow_ids` (meaning "has no flows") both resolve to scope `"all"`. A cached admin response can be served to a non-admin — cross-user data leak.

**Acceptance:** Document the exact collision scenario. No code changes in this task.

---

## Task 1 — Fix cache key collision (BUG-L4)

**File:** `src/backend/base/langflow/services/langwatch/service.py`

**Change `_build_cache_key` signature** (line 477) — add `is_admin: bool` parameter:

```python
def _build_cache_key(
    self,
    params: UsageQueryParams,
    allowed_flow_ids: set[UUID],
    org_id: str,
    *,
    is_admin: bool = False,
) -> str:
```

**Replace lines 496-501** with role-aware scoping:

```python
if params.user_id:
    user_scope = str(params.user_id)
elif is_admin and len(allowed_flow_ids) == 0:
    user_scope = "admin:all"
elif len(allowed_flow_ids) == 0:
    user_scope = "user:none"  # non-admin with zero flows — must NOT collide with admin
else:
    user_scope = "user"
```

**Update `get_usage_summary` signature** (line 511) — add `is_admin` as a **keyword-only** parameter using `*` separator:

```python
async def get_usage_summary(
    self,
    params: UsageQueryParams,
    allowed_flow_ids: set[UUID],
    api_key: str,
    org_id: str = "default",
    *,
    is_admin: bool = False,
) -> UsageSummaryResponse:
```

**Update call site** at line 535 — pass `is_admin` through to `_build_cache_key`.

**Update router call site** at `router.py:197` — add `is_admin=current_user.is_superuser` to the `get_usage_summary` call:

```python
result = await langwatch_service.get_usage_summary(
    params, allowed_flow_ids, api_key, org_id="default",
    is_admin=current_user.is_superuser,
)
```

**Test:** Two calls — admin with empty flows, non-admin with empty flows. Assert different cache keys.

**Update existing tests** in `test_langwatch_caching.py`:
- `test_cache_key_schema_no_user_id_empty_allowed` — currently asserts scope `"all"` for empty `allowed_flow_ids` with non-admin (default `is_admin=False`). Update to expect `"user:none"`.
- `test_cache_key_schema_mcp_sub_view` — same fix: update expected scope from `"all"` to `"user:none"` where `is_admin` defaults to `False`.
- **Add new test cases** for `is_admin=True` with empty `allowed_flow_ids` set — expect scope `"admin:all"`.

---

## Task 2 — Fix DateRange serialization alias (BUG-I1)

**File:** `src/backend/base/langflow/services/langwatch/service.py` line 565

**Current:** `aggregated.model_dump_json()` — serializes `from_` (Python field name), not `from` (JSON alias).
**Fix:** Change to `aggregated.model_dump_json(by_alias=True)`.

**Schemas context:** `schemas.py:34` defines `from_: date | None = Field(None, alias="from")` with `model_config = {"populate_by_name": True}`. The API response uses `response_model` which serializes by alias. Cache must match.

**Test:** Round-trip: serialize → deserialize via `model_validate_json`. Assert `from_` field is populated.

---

## Task 3 — Fix org_id misuse (BUG-L10)

**File:** `src/backend/base/langflow/api/v1/usage/router.py` line 194

**Current:** `org_id=str(current_user.id)` — uses user ID as org ID. Every user gets a unique cache namespace, killing cache hit rate for multi-user orgs.

**Decision:** For single-org deployments (current Langbuilder model), use a fixed org ID `"default"` which matches the `get_usage_summary` default parameter. If multi-org support is added later, replace with `current_user.org_id`.

**Fix:** Change `org_id=str(current_user.id)` to `org_id="default"` at line 194 (and any other call sites — check lines ~255, ~280 in router.py).

**Test:** Two users in same deployment hit the same cache namespace.

---

## Task 4 — Document Redis status (BUG-L1)

**File:** `src/backend/base/langflow/services/langwatch/service.py` lines 930-935

**Current:** `from lfx.services.deps import get_redis_client` always fails silently. `redis_client` is always `None`. The entire cache-aside pattern in `get_usage_summary` (lines 538-568) never executes.

**DO NOT** attempt to fix the Redis integration — that is a separate feature.

**Changes:**
1. Add a `# TODO(redis): ...` comment at line 930 explaining the dead import.
2. Verify all cache operations already gracefully no-op when `self.redis is None`:
   - `get_usage_summary` line 538: `if self.redis is not None` — OK
   - `get_usage_summary` line 560: `if self.redis is not None` — OK
   - `invalidate_cache` line 901: `if self.redis is None: return` — OK
3. No functional code changes.

---

## Task 5 — Verify no cross-user data leakage

**Goal:** End-to-end confirmation that Tasks 1-4 are correct.

**Test matrix:**

| Scenario | `is_admin` | `allowed_flow_ids` | Expected scope |
|----------|-----------|-------------------|---------------|
| Admin, all flows | `True` | `{}` (empty) | `admin:all` |
| Non-admin, no flows | `False` | `{}` (empty) | `user:none` |
| Non-admin, has flows | `False` | `{uuid1, uuid2}` | `user` |
| Filtered by user_id | either | any | `<user_id>` |

**Verify:**
1. Cache keys for rows 1 and 2 are different strings.
2. `model_dump_json(by_alias=True)` round-trips correctly with `model_validate_json`.
3. `org_id="default"` appears in all cache keys.
4. Redis `None` path does not raise.
