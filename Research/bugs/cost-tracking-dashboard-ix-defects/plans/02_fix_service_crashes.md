---
skill: serious-plan
slug: fix-service-crashes
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 02: Fix Service Crashes (BUG-C3, BUG-C4, BUG-L3)

**Priority:** 2 CRASH -- endpoints crash on normal usage
**Bugs:** BUG-C3 (null dates crash), BUG-C4 (unhandled httpx errors), BUG-L3 (missing error handling in `get_usage_summary`)
**Depends on:** Plan 01 (DI must work before these code paths are reachable)
**Sync pairs:** `_fetch_from_langwatch` must match `fetch_flow_runs` for date handling and error handling

---

## Task 0 -- Smoke Test (capture the crash)

**Intent:** Prove that calling the endpoint without date params crashes after Plan 01 is applied.

**Steps:**
1. Apply Plan 01 fixes, restart server, save a valid LangWatch key.
2. `curl -H "Authorization: Bearer <token>" http://localhost:7860/api/v1/usage/`
   (no `from_date` or `to_date` params)
3. Capture the `AttributeError: 'NoneType' object has no attribute 'timestamp'` traceback.

**Acceptance:**
- [ ] Request returns 500 with traceback referencing `service.py` line 260 or 261

**Rollback:** N/A (read-only observation)

---

## Task 1 -- Fix null date handling in `_fetch_from_langwatch`

**Intent:** Add null checks for `from_dt`/`to_dt` so that omitting date params defaults to sensible values instead of crashing. Must match the pattern already used in `fetch_flow_runs` (lines 633-638).

**File:** `src/backend/base/langflow/services/langwatch/service.py`

**Changes at lines 260-261:**

```python
# BEFORE (lines 260-261):
start_ms = int(from_dt.timestamp() * 1000)
end_ms = int(to_dt.timestamp() * 1000)

# AFTER (matching fetch_flow_runs lines 633-638):
start_ms = int(from_dt.timestamp() * 1000) if from_dt else 0
end_ms = (
    int(to_dt.timestamp() * 1000)
    if to_dt
    else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
)
```

**Sync pair check:** `fetch_flow_runs` (line 633) uses `if from_datetime else 0` for start and `if to_datetime else int(datetime.now(...))` for end. This change mirrors that exactly.

**Acceptance:**
- [ ] `_fetch_from_langwatch` handles `None` dates without crashing
- [ ] Default behavior: `from_date=None` maps to epoch 0, `to_date=None` maps to now
- [ ] Pattern matches `fetch_flow_runs` lines 633-638 exactly
- [ ] File passes `ruff check`

**Rollback:** `git checkout -- src/backend/base/langflow/services/langwatch/service.py`

---

## Task 2 -- Fix httpx error handling

**Intent:** Catch `httpx.HTTPStatusError` in `_fetch_all_pages` and wrap in `LangWatchError` subclasses. Also add try/except in `get_usage_summary` matching the `fetch_flow_runs` pattern (lines 641-652).

**File:** `src/backend/base/langflow/services/langwatch/service.py`

**Change A -- `_fetch_all_pages` (after line 211):**

```python
# BEFORE (line 211):
response.raise_for_status()

# AFTER:
try:
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    from langflow.services.langwatch.exceptions import (
        LangWatchInvalidKeyError,
        LangWatchUnavailableError,
    )
    if exc.response.status_code in (401, 403):
        msg = f"LangWatch rejected the API key: {exc.response.status_code}"
        raise LangWatchInvalidKeyError(msg) from exc
    msg = f"LangWatch API error: {exc.response.status_code}"
    raise LangWatchUnavailableError(msg) from exc
```

**Change B -- `get_usage_summary` (wrap the fetch call at line 555):**

```python
# BEFORE (lines 554-557):
# 2. Cache miss -- fetch from LangWatch
raw_data = await self._fetch_from_langwatch(params, api_key)
filtered, flow_map = await self._filter_by_ownership(raw_data, allowed_flow_ids)
aggregated = self._aggregate_with_metadata(filtered, params, flow_name_map=flow_map)

# AFTER (matching fetch_flow_runs lines 641-652):
# 2. Cache miss -- fetch from LangWatch
try:
    raw_data = await self._fetch_from_langwatch(params, api_key)
except httpx.TimeoutException as exc:
    from langflow.services.langwatch.exceptions import LangWatchUnavailableError
    msg = f"LangWatch request timed out: {exc}"
    raise LangWatchUnavailableError(msg) from exc
except httpx.TransportError as exc:
    from langflow.services.langwatch.exceptions import LangWatchUnavailableError
    msg = f"LangWatch connection error: {exc}"
    raise LangWatchUnavailableError(msg) from exc
filtered, flow_map = await self._filter_by_ownership(raw_data, allowed_flow_ids)
aggregated = self._aggregate_with_metadata(filtered, params, flow_name_map=flow_map)
```

**Sync pair check:** `fetch_flow_runs` (lines 641-652) catches `httpx.TimeoutException` and `httpx.TransportError`, wraps both in `LangWatchUnavailableError`. This change mirrors that pattern. The `_fetch_all_pages` change additionally catches `HTTPStatusError` (the `raise_for_status()` path) which neither caller previously handled.

**Acceptance:**
- [ ] `_fetch_all_pages` catches `httpx.HTTPStatusError` and wraps in `LangWatchError` subclass
- [ ] 401/403 from LangWatch raises `LangWatchInvalidKeyError`
- [ ] Other HTTP errors raise `LangWatchUnavailableError`
- [ ] `get_usage_summary` catches `TimeoutException` and `TransportError` (matching `fetch_flow_runs`)
- [ ] Router's `except LangWatchError` now catches all error paths
- [ ] File passes `ruff check`

**Rollback:** `git checkout -- src/backend/base/langflow/services/langwatch/service.py`

---

## Task 2.5 -- Update test assertions for new exception types

**Intent:** The existing tests in `test_langwatch_fetch.py` assert `httpx.HTTPStatusError` for 401/403 and 5xx scenarios. After Task 2 wraps those errors in `LangWatchInvalidKeyError` and `LangWatchUnavailableError`, the test assertions must be updated to match.

**File:** `src/backend/base/tests/unit/test_langwatch_fetch.py`

**Changes:**
1. **Add imports** at top of file:
   ```python
   from langflow.services.langwatch.exceptions import (
       LangWatchInvalidKeyError,
       LangWatchUnavailableError,
   )
   ```
2. **Line 336:** Change `pytest.raises(httpx.HTTPStatusError)` to `pytest.raises(LangWatchInvalidKeyError)`
3. **Line 349:** Change `pytest.raises(httpx.HTTPStatusError)` to `pytest.raises(LangWatchUnavailableError)`

**Acceptance:**
- [ ] Line 336 asserts `LangWatchInvalidKeyError` (not `httpx.HTTPStatusError`)
- [ ] Line 349 asserts `LangWatchUnavailableError` (not `httpx.HTTPStatusError`)
- [ ] Both exception classes are imported from `langflow.services.langwatch.exceptions`
- [ ] Tests pass: `pytest tests/unit/test_langwatch_fetch.py`

**Rollback:** `git checkout -- src/backend/base/tests/unit/test_langwatch_fetch.py`

---

## Task 3 -- Verify

**Intent:** Confirm endpoints handle missing dates and LangWatch errors gracefully.

**Steps:**
1. Restart the dev server.
2. `curl -H "Authorization: Bearer <token>" http://localhost:7860/api/v1/usage/`
   (no date params) -- Expected: 200 with data or 503 structured error, NOT 500
3. `curl -H "Authorization: Bearer <token>" "http://localhost:7860/api/v1/usage/?from_date=2026-01-01&to_date=2026-03-17"`
   (with date params) -- Expected: 200 with data or 503 structured error
4. Test with invalid/expired LangWatch key -- Expected: 422 `INVALID_KEY`, NOT raw 500

**Acceptance:**
- [ ] No date params: returns 200 or structured error (not 500)
- [ ] With date params: returns 200 or structured error (not 500)
- [ ] Invalid key scenario: returns 422 `INVALID_KEY` (not raw 500 traceback)
- [ ] No `AttributeError` or `httpx.HTTPStatusError` in server logs

**Rollback:** Full plan rollback: `git checkout -- src/backend/base/langflow/services/langwatch/service.py`
