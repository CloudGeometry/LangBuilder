---
skill: serious-plan
slug: fix-migration-and-model
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 03: Fix Migration and Model (BUG-L9, BUG-L8)

**Priority:** 3 -- blocks all SQLite deployments
**Bugs:** BUG-L9 (`sa.text("NOW()")` incompatible with SQLite), BUG-L8 (`datetime.utcnow` deprecated, naive/aware tz mixing)
**Sync pair:** `global_settings.py` datetime defaults must match `service.py save_key` datetime usage (line 773: `datetime.now(tz=timezone.utc)`)

---

## Task 0 -- Smoke Test (capture the SQLite error)

**Intent:** Prove the migration fails on SQLite before making changes.

**Steps:**
1. Configure SQLite database URL (e.g., `sqlite+aiosqlite:///./test.db`).
2. Run `alembic upgrade head`.
3. Capture the error: `sqlalchemy.exc.OperationalError: near "NOW": syntax error`.

**Acceptance:**
- [ ] Migration fails with SQLite syntax error referencing `NOW()`

**Rollback:** N/A (read-only observation)

---

## Task 1 -- Fix migration `NOW()` calls

**Intent:** Replace PostgreSQL-only `sa.text("NOW()")` with the cross-database `sa.func.now()` which SQLAlchemy renders as `CURRENT_TIMESTAMP` on SQLite and `NOW()` on PostgreSQL.

**File:** `src/backend/base/langflow/alembic/versions/773db17e6029_add_global_settings_table.py`

**Changes:**
1. **Line 31** -- `created_at` server default:
   ```python
   # BEFORE:
   server_default=sa.text("NOW()"),

   # AFTER:
   server_default=sa.func.now(),
   ```

2. **Line 37** -- `updated_at` server default:
   ```python
   # BEFORE:
   server_default=sa.text("NOW()"),

   # AFTER:
   server_default=sa.func.now(),
   ```

**Acceptance:**
- [ ] No `sa.text("NOW()")` remains in the migration file
- [ ] Both `created_at` and `updated_at` use `sa.func.now()`
- [ ] File passes `ruff check`

**Rollback:** `git checkout -- src/backend/base/langflow/alembic/versions/773db17e6029_add_global_settings_table.py`

---

## Task 2 -- Fix model `datetime.utcnow` deprecation

**Intent:** Replace deprecated `datetime.utcnow` (returns naive datetime) with `datetime.now(tz=timezone.utc)` (returns aware datetime). This eliminates the naive/aware mismatch with `service.py save_key` (line 773) which already uses `datetime.now(tz=timezone.utc)`.

**File:** `src/backend/base/langflow/services/database/models/global_settings.py`

**Changes:**
1. **Line 1** -- update import:
   ```python
   # BEFORE:
   from datetime import datetime

   # AFTER:
   from datetime import datetime, timezone
   ```

2. **Line 21** -- `created_at` default:
   ```python
   # BEFORE:
   created_at: datetime = Field(default_factory=datetime.utcnow)

   # AFTER:
   created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
   ```

3. **Line 22** -- `updated_at` default:
   ```python
   # BEFORE:
   updated_at: datetime = Field(default_factory=datetime.utcnow)

   # AFTER:
   updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
   ```

**Sync pair check:** `service.py save_key` (line 773) uses `datetime.now(tz=timezone.utc)`. After this fix, both model defaults and service code produce timezone-aware UTC datetimes -- no more `TypeError` from mixing naive and aware.

**Acceptance:**
- [ ] No `datetime.utcnow` remains in `global_settings.py`
- [ ] Both fields use `datetime.now(tz=timezone.utc)` via lambda
- [ ] `timezone` is imported from `datetime`
- [ ] File passes `ruff check`

**Rollback:** `git checkout -- src/backend/base/langflow/services/database/models/global_settings.py`

---

## Task 3 -- Verify

**Intent:** Confirm the migration runs on SQLite and the model produces correct datetimes.

**Steps:**
1. Delete any existing test SQLite DB.
2. Configure `LANGFLOW_DATABASE_URL=sqlite+aiosqlite:///./test_migration.db`.
3. Run `alembic upgrade head`.
4. Verify `global_settings` table exists: `sqlite3 test_migration.db ".schema global_settings"`.
5. Verify `DEFAULT (CURRENT_TIMESTAMP)` appears in the schema output for both `created_at` and `updated_at`.

**Acceptance:**
- [ ] `alembic upgrade head` completes without error on SQLite
- [ ] `global_settings` table exists with correct schema
- [ ] `created_at` and `updated_at` have `CURRENT_TIMESTAMP` defaults
- [ ] No `NOW()` in the rendered SQLite schema

**Rollback:** Full plan rollback:
```
git checkout -- src/backend/base/langflow/alembic/versions/773db17e6029_add_global_settings_table.py
git checkout -- src/backend/base/langflow/services/database/models/global_settings.py
```
