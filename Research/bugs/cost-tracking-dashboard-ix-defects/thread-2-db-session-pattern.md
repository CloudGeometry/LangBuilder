# Thread 2: DB Session Dependency Pattern Analysis

## Summary

The usage router defines its own broken `_injectable_db_session` wrapper that treats `injectable_session_scope()` as an async context manager (`async with`), but it is actually a bare async generator designed for FastAPI's `Depends()`. Every other router that needs a DB session imports the canonical `DbSession` type alias from `langflow.api.utils`, which is wired directly to `Depends(injectable_session_scope)`. The usage router is the **only** router in the codebase with this bug.

---

## 1. All Router Files in `src/backend/base/langflow/api/v1/`

Files that define `APIRouter` instances (i.e., actual route modules):

| # | File | Has DB session? |
|---|------|----------------|
| 1 | `api_key.py` | Yes |
| 2 | `chat.py` | Yes |
| 3 | `endpoints.py` | Yes |
| 4 | `files.py` | Yes |
| 5 | `flows.py` | Yes |
| 6 | `folders.py` | No (redirect-only stubs) |
| 7 | `knowledge_bases.py` | No |
| 8 | `login.py` | Yes |
| 9 | `mcp.py` | No (MCP session manager, not DB) |
| 10 | `mcp_projects.py` | Yes (via `session_scope()` context manager) |
| 11 | `model_options.py` | No |
| 12 | `models.py` | Yes |
| 13 | `monitor.py` | Yes |
| 14 | `openai_responses.py` | No |
| 15 | `projects.py` | Yes |
| 16 | `starter_projects.py` | No |
| 17 | `store.py` | No |
| 18 | `traces.py` | Yes (via `session_scope()` context manager) |
| 19 | **`usage/router.py`** | **Yes (BROKEN custom wrapper)** |
| 20 | `users.py` | Yes |
| 21 | `validate.py` | No |
| 22 | `variable.py` | Yes |
| 23 | `voice_mode.py` | Yes |

Non-router files in the same directory (`auth_helpers.py`, `base.py`, `callback.py`, `mcp_utils.py`, `schemas.py`, `__init__.py`) do not define `APIRouter` instances.

---

## 2. Session Pattern Used by Each Router

### Pattern A: Canonical `DbSession` import (11 routers)

All of these import `DbSession` from `langflow.api.utils` (which re-exports from `langflow.api.utils.core`):

```python
from langflow.api.utils import DbSession
# or
from langflow.api.utils import CurrentActiveUser, DbSession
```

Then use it as a FastAPI parameter annotation:

```python
async def my_endpoint(session: DbSession, ...):
```

**Routers using Pattern A:**

| Router | Import line | Line # |
|--------|------------|--------|
| `api_key.py` | `from langflow.api.utils import CurrentActiveUser, DbSession` | 5 |
| `chat.py` | `from langflow.api.utils import ... DbSession ...` | 19-21 |
| `endpoints.py` | `from langflow.api.utils import CurrentActiveUser, DbSession, ...` | 30 |
| `files.py` | `from langflow.api.utils import CurrentActiveUser, DbSession, ValidatedFileName` | 15 |
| `flows.py` | `from langflow.api.utils import CurrentActiveUser, DbSession, ...` | 24 |
| `login.py` | `from langflow.api.utils import DbSession` | 9 |
| `models.py` | `from langflow.api.utils import CurrentActiveUser, DbSession` | 18 |
| `monitor.py` | `from langflow.api.utils import DbSession, custom_params` | 10 |
| `projects.py` | `from langflow.api.utils import CurrentActiveUser, DbSession, ...` | 21 |
| `users.py` | `from langflow.api.utils import CurrentActiveUser, DbSession` | 10 |
| `variable.py` | `from langflow.api.utils import CurrentActiveUser, DbSession` | 10 |
| `voice_mode.py` | `from langflow.api.utils import CurrentActiveUser, DbSession` | 27 |

### Pattern B: Direct `session_scope()` context manager (2 routers)

These use `async with session_scope() as session:` inside endpoint bodies (not via `Depends`):

| Router | Import | Usage |
|--------|--------|-------|
| `traces.py` (line 33) | `from langflow.services.deps import session_scope` | `async with session_scope() as session:` (lines 150, 182) |
| `mcp_projects.py` (line 23) | `from lfx.services.deps import ... session_scope` | `async with session_scope() as session:` (lines 156, 223, 332, etc.) |

These are **correct** -- `session_scope()` is an `@asynccontextmanager` and is designed for `async with`.

### Pattern C: BROKEN custom wrapper (1 router -- usage only)

```python
# usage/router.py lines 47-55
async def _injectable_db_session() -> AsyncSession:
    """Resolve an async DB session via lfx DI scope."""
    from lfx.services.deps import injectable_session_scope

    async with injectable_session_scope() as session:  # <-- BUG
        yield session

DbSession = Annotated[AsyncSession, Depends(_injectable_db_session)]
```

---

## 3. The Canonical `DbSession` Definition

**File:** `src/backend/base/langflow/api/utils/core.py`, lines 13 and 40

```python
# line 13
from lfx.services.deps import injectable_session_scope, injectable_session_scope_readonly, session_scope

# line 40
DbSession = Annotated[AsyncSession, Depends(injectable_session_scope)]
```

This is re-exported via `src/backend/base/langflow/api/utils/__init__.py` (line 15):

```python
from langflow.api.utils.core import (
    ...
    DbSession,
    ...
)
```

---

## 4. The `injectable_session_scope` Implementation

**File:** `src/lfx/src/lfx/services/deps.py`, lines 149-151

```python
async def injectable_session_scope():
    async with session_scope() as session:
        yield session
```

This is a **bare async generator function** -- it uses `yield`, not `return`. It is **not** decorated with `@asynccontextmanager`. This is exactly the signature FastAPI expects for `Depends()` -- FastAPI's dependency injection system knows how to consume async generators: it iterates to the `yield`, provides the value, and then continues iteration for cleanup.

**Contrast with `session_scope()`** (lines 154-192):

```python
@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    db_service = get_db_service()
    async with db_service._with_session() as session:
        try:
            yield session
            await session.commit()
        except HTTPException:
            if session.is_active:
                with suppress(InvalidRequestError):
                    await session.rollback()
            raise
        except Exception as e:
            await logger.aexception(...)
            if session.is_active:
                with suppress(InvalidRequestError):
                    await session.rollback()
            raise
```

`session_scope()` **is** decorated with `@asynccontextmanager`, making it an async context manager suitable for `async with`.

### Key distinction:

| Function | Decorator | Usage |
|----------|-----------|-------|
| `injectable_session_scope()` | None (bare async generator) | `Depends(injectable_session_scope)` |
| `session_scope()` | `@asynccontextmanager` | `async with session_scope() as session:` |

---

## 5. What the Usage Router Does Wrong

**File:** `src/backend/base/langflow/api/v1/usage/router.py`, lines 47-55

The usage router wraps `injectable_session_scope()` inside `async with`, treating it as a context manager:

```python
async def _injectable_db_session() -> AsyncSession:
    from lfx.services.deps import injectable_session_scope
    async with injectable_session_scope() as session:  # BUG HERE
        yield session
```

**Why this is wrong:**

`injectable_session_scope()` is a bare async generator, NOT an `@asynccontextmanager`. Calling `async with` on it will fail because async generators do not implement the `__aenter__`/`__aexit__` protocol. Specifically:

1. `injectable_session_scope()` returns an `AsyncGenerator` object
2. `async with` requires an object with `__aenter__` and `__aexit__`
3. Bare async generators do not have these methods
4. This raises `AttributeError: 'async_generator' object does not support the asynchronous context manager protocol`

The error would occur at runtime when any usage endpoint that injects `DbSession` is called (i.e., `GET /api/v1/usage/` and `GET /api/v1/usage/{flow_id}/runs`).

---

## 6. Complete Comparison Table

| Router file | Session pattern | Source of `DbSession` | Works? |
|------------|----------------|----------------------|--------|
| `api_key.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `chat.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `endpoints.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `files.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `flows.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `folders.py` | N/A (no DB access) | N/A | YES |
| `knowledge_bases.py` | N/A (no DB access) | N/A | YES |
| `login.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `mcp.py` | N/A (no DB session) | N/A | YES |
| `mcp_projects.py` | `async with session_scope()` (inline) | `lfx.services.deps` | YES |
| `model_options.py` | N/A (no DB access) | N/A | YES |
| `models.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `monitor.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `openai_responses.py` | N/A (no DB access) | N/A | YES |
| `projects.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `starter_projects.py` | N/A (no DB access) | N/A | YES |
| `store.py` | N/A (no DB access) | N/A | YES |
| `traces.py` | `async with session_scope()` (inline) | `langflow.services.deps` | YES |
| **`usage/router.py`** | **`Depends(_injectable_db_session)` with broken `async with injectable_session_scope()`** | **Local redefinition** | **NO** |
| `users.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `validate.py` | N/A (no DB access) | N/A | YES |
| `variable.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |
| `voice_mode.py` | `Depends(injectable_session_scope)` via imported `DbSession` | `langflow.api.utils` | YES |

---

## 7. The Fix

### What to change in `usage/router.py`

**Delete** lines 44-55 (the broken `_injectable_db_session` function and the local `DbSession` / `CurrentActiveUser` redefinitions):

```python
# DELETE THIS BLOCK (lines 44-57):
# ── Session dependency ────────────────────────────────────────────────────────

async def _injectable_db_session() -> AsyncSession:  # pragma: no cover
    """Resolve an async DB session via lfx DI scope."""
    from lfx.services.deps import injectable_session_scope

    async with injectable_session_scope() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(_injectable_db_session)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
```

**Add** the canonical imports instead:

```python
from langflow.api.utils import CurrentActiveUser, DbSession
```

This also allows removing these now-unnecessary imports from the file header:
- `from typing import Annotated` (if only used for DbSession/CurrentActiveUser -- check if still needed for Query params)
- `from fastapi import Depends` (if only used for DbSession/CurrentActiveUser -- check if still needed for LangWatchDep)
- `from sqlmodel.ext.asyncio.session import AsyncSession` (if only used in the DbSession alias and _get_flow_ids_for_user type hint)

**Note:** `Annotated` is still used for `LangWatchDep` (line 58) and Query parameters, `Depends` is still used for `LangWatchDep`, and `AsyncSession` is still used in the `_get_flow_ids_for_user` type hint (line 65). So only `CurrentActiveUser` and `DbSession` lines need to change -- the header imports can stay.

### Minimal diff

```diff
--- a/src/backend/base/langflow/api/v1/usage/router.py
+++ b/src/backend/base/langflow/api/v1/usage/router.py
@@ -16,6 +16,7 @@ from sqlmodel.ext.asyncio.session import AsyncSession

 from langflow.services.auth.utils import get_current_active_superuser, get_current_active_user
+from langflow.api.utils import CurrentActiveUser, DbSession
 from langflow.services.database.models.flow.model import Flow
 from langflow.services.database.models.user.model import User
 from langflow.services.langwatch.exceptions import (
@@ -41,18 +42,8 @@ from langflow.services.langwatch.service import LangWatchService, get_langwatch_
 router = APIRouter(prefix="/usage", tags=["Usage & Cost Tracking"])


-# ── Session dependency ────────────────────────────────────────────────────────
-
-
-async def _injectable_db_session() -> AsyncSession:  # pragma: no cover
-    """Resolve an async DB session via lfx DI scope."""
-    from lfx.services.deps import injectable_session_scope
-
-    async with injectable_session_scope() as session:
-        yield session
-
-
-DbSession = Annotated[AsyncSession, Depends(_injectable_db_session)]
-CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
 CurrentSuperUser = Annotated[User, Depends(get_current_active_superuser)]
 LangWatchDep = Annotated[LangWatchService, Depends(get_langwatch_service)]
```

---

## 8. Other Routers Using the Broken Pattern

**None.** The usage router is the only router in the entire `langflow/api/` tree that redefines `DbSession` locally or wraps `injectable_session_scope()` with `async with`. Every other router either:
- Imports `DbSession` from `langflow.api.utils` (canonical pattern), or
- Uses `async with session_scope()` directly (correct context-manager usage), or
- Does not use database sessions at all.

---

## 9. File Paths Referenced

All paths relative to codebase root: `src/backend/base/langflow/`

| File | Key lines | Role |
|------|-----------|------|
| `api/utils/core.py` | 13, 37, 40, 42 | Canonical `DbSession`, `DbSessionReadOnly`, `CurrentActiveUser` definitions |
| `api/utils/__init__.py` | 15 | Re-exports `DbSession` |
| `api/v1/usage/router.py` | 47-55 | **BROKEN** local `_injectable_db_session` + `DbSession` redefinition |
| `services/deps.py` | 154-156, 159-177 | `get_session` (deprecated), `session_scope` (context manager) |

Absolute path to lfx deps:
- `src/lfx/src/lfx/services/deps.py` lines 149-151 (`injectable_session_scope` -- bare async generator), lines 154-192 (`session_scope` -- `@asynccontextmanager`)
