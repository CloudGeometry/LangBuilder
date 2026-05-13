---
skill: serious-plan
slug: fix-di-crashes
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 01: Fix DI Crashes (BUG-C1, BUG-C2)

**Priority:** 1 CRITICAL -- blocks ALL usage endpoints
**Bugs:** BUG-C1 (router `_injectable_db_session`), BUG-C2 (service `_injectable_session`)
**Side-effect fix:** Eliminates dual-session BUG-L4 vector (service now shares the router's session)
**Root cause:** Both files wrap a bare async generator (`injectable_session_scope`) with `async with`, which raises `AttributeError: __aenter__`. The canonical pattern uses `Depends(injectable_session_scope)` directly, as seen in `langflow/api/utils/core.py:40`.

---

## Task 0 -- Smoke Test (capture the crash)

**Intent:** Prove the crash exists before making changes.

**Steps:**
1. Start the dev server.
2. `curl -H "Authorization: Bearer <token>" http://localhost:7860/api/v1/usage/`
3. Capture the `AttributeError` traceback in the response or server logs.

**Acceptance:**
- [ ] Request returns 500 with `AttributeError` mentioning `__aenter__`

**Rollback:** N/A (read-only observation)

---

## Task 1 -- Fix `router.py` DI

**Intent:** Replace the broken local session/user dependencies with the canonical imports used by every other router.

**File:** `src/backend/base/langflow/api/v1/usage/router.py`

**Changes:**
1. **Delete lines 44-56** -- remove `_injectable_db_session` function, local `DbSession`, and local `CurrentActiveUser`:
   ```
   # DELETE: lines 44-56
   # ── Session dependency ──────────────────────────────
   async def _injectable_db_session() -> AsyncSession: ...
   DbSession = Annotated[AsyncSession, Depends(_injectable_db_session)]
   CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
   ```
2. **Add import** (after existing imports, ~line 18):
   ```python
   from langflow.api.utils import CurrentActiveUser, DbSession
   ```
3. **Clean up imports** after deleting the local DI code:
   - **Keep `from typing import Annotated`** (line 11) -- Annotated is still used by `CurrentSuperUser`, `LangWatchDep`, and `Query` params. Do NOT remove.
   - **Move `AsyncSession` to a `TYPE_CHECKING` block** instead of deleting it -- it is still used as a type hint in `_get_flow_ids_for_user`. Replace `from sqlmodel.ext.asyncio.session import AsyncSession` (line 16) with:
     ```python
     from typing import TYPE_CHECKING

     if TYPE_CHECKING:
         from sqlmodel.ext.asyncio.session import AsyncSession
     ```
   - Keep `from fastapi import ... Depends ...` because `CurrentSuperUser` and `LangWatchDep` still use it

**Acceptance:**
- [ ] `_injectable_db_session` function no longer exists in `router.py`
- [ ] `DbSession` and `CurrentActiveUser` are imported from `langflow.api.utils`
- [ ] `from typing import Annotated` is still present (used by `CurrentSuperUser`, `LangWatchDep`, `Query` params)
- [ ] `AsyncSession` import is inside a `TYPE_CHECKING` block (not at top-level)
- [ ] No `injectable_session_scope` import remains in `router.py`
- [ ] File passes `ruff check` with no errors

**Rollback:** `git checkout -- src/backend/base/langflow/api/v1/usage/router.py`

---

## Task 2 -- Fix `service.py` DI

**Intent:** Remove the broken `_injectable_session` shim. Have `get_langwatch_service` accept a session from the canonical `DbSession` dependency, which also eliminates the dual-session problem (service and router now share one session).

**File:** `src/backend/base/langflow/services/langwatch/service.py`

**Changes:**
1. **Delete lines 105-118** -- remove the `_injectable_session` function and its comment block:
   ```
   # DELETE: lines 105-118
   # ── DI helper ──────────────────────────────
   async def _injectable_session(): ...
   ```
2. **Update `get_langwatch_service`** (line 915-936) -- change the session parameter from `Depends(_injectable_session)` to use `Depends(injectable_session_scope)` (the canonical session dependency). Do NOT use bare `Depends()` -- bare `Depends()` tries to instantiate `AsyncSession` directly, which fails.
   ```python
   # ADD import at top of file:
   from lfx.services.deps import injectable_session_scope

   # BEFORE (line 916):
   def get_langwatch_service(
       session: AsyncSession = Depends(_injectable_session),
   ) -> LangWatchService:

   # AFTER:
   def get_langwatch_service(
       session: AsyncSession = Depends(injectable_session_scope),
   ) -> LangWatchService:
   ```
3. **Keep the `Depends` import from `fastapi`** (line 46) -- it is still used in `get_langwatch_service`.

**Acceptance:**
- [ ] `_injectable_session` function no longer exists in `service.py`
- [ ] `get_langwatch_service` uses `Depends(injectable_session_scope)` matching the canonical pattern
- [ ] No `async with injectable_session_scope()` pattern remains in `service.py`
- [ ] File passes `ruff check` with no errors

**Rollback:** `git checkout -- src/backend/base/langflow/services/langwatch/service.py`

---

## Task 2.5 -- Update test dependency overrides

**Intent:** The integration tests override `_injectable_db_session` to inject a test session. Since Task 1 deleted that function, the overrides must point to `injectable_session_scope` instead.

**File:** `src/backend/base/tests/unit/test_usage_api_integration.py`

**Changes:**
1. **Add import** at top of file:
   ```python
   from lfx.services.deps import injectable_session_scope
   ```
2. **Line 168:** Change `app.dependency_overrides[mod._injectable_db_session]` to `app.dependency_overrides[injectable_session_scope]`
3. **Line 415:** Change `app.dependency_overrides[mod._injectable_db_session]` to `app.dependency_overrides[injectable_session_scope]`

**Acceptance:**
- [ ] No reference to `_injectable_db_session` remains in `test_usage_api_integration.py`
- [ ] Both overrides (lines 168 and 415) now use `injectable_session_scope`
- [ ] `from lfx.services.deps import injectable_session_scope` is present in the test imports
- [ ] Tests pass: `pytest tests/unit/test_usage_api_integration.py`

**Rollback:** `git checkout -- src/backend/base/tests/unit/test_usage_api_integration.py`

---

## Task 3 -- Verify

**Intent:** Confirm all four endpoints respond without DI crashes.

**Steps:**
1. Restart the dev server.
2. `curl -H "Authorization: Bearer <token>" http://localhost:7860/api/v1/usage/`
   - Expected: 503 `KEY_NOT_CONFIGURED` (correct -- no LangWatch key saved yet)
3. `curl -H "Authorization: Bearer <token>" http://localhost:7860/api/v1/usage/settings/langwatch-key/status`
   - Expected: 200 `{"has_key": false}` or 503 -- NOT a 500 `AttributeError`
4. Verify no `AttributeError` or `__aenter__` in server logs.

**Acceptance:**
- [ ] GET `/api/v1/usage/` returns 503 `KEY_NOT_CONFIGURED` (not 500)
- [ ] GET `/api/v1/usage/settings/langwatch-key/status` returns 200 or 403 (not 500)
- [ ] No `AttributeError` in server logs
- [ ] No `__aenter__` in server logs

**Rollback:** Full plan rollback: `git checkout -- src/backend/base/langflow/api/v1/usage/router.py src/backend/base/langflow/services/langwatch/service.py`
