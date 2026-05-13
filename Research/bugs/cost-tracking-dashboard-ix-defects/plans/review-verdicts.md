# Plan Review Verdicts

## Summary

| Plan | Verdict | Issues Found |
|------|---------|-------------|
| 01 — DI Crashes | NEEDS ADJUSTMENT | 4 issues: don't remove Annotated/AsyncSession imports, use Depends(injectable_session_scope) not bare Depends(), update test overrides |
| 02 — Service Crashes | NEEDS ADJUSTMENT | 1 issue: update 2 existing tests that assert httpx.HTTPStatusError |
| 03 — Migration & Model | SAFE | No issues. sa.func.now() confirmed cross-dialect. |
| 04 — Security & Cache | NEEDS ADJUSTMENT | 2 issues: update cache key tests, specify is_admin as keyword-only in get_usage_summary |
| 05 — Frontend Errors | NEEDS ADJUSTMENT | 3 issues: LangWatchKeyForm.getErrorMessage breaks, ErrorState.getErrorCode breaks, service test assertions break |
| 06 — Service Cleanup | NEEDS ADJUSTMENT | 4 issues: Task 2 (flow name→ID) is UNSAFE as written (traces don't have flow IDs), test updates needed for Tasks 3-4, exec/execute line 752 can't be naively changed |
| 07 — Navigation | NEEDS ADJUSTMENT | 3 issues: E2E test + unit test click usage-tab, default flag=false blocks verification, wrap loading state in PageLayout |

## Critical Adjustments Required

### Plan 01
1. **Keep `from typing import Annotated`** — still used by CurrentSuperUser, LangWatchDep, Query params
2. **Move AsyncSession to TYPE_CHECKING** — don't delete, still used in _get_flow_ids_for_user type hint
3. **Service fix: use `Depends(injectable_session_scope)` not bare `Depends()`** — bare Depends tries to instantiate AsyncSession
4. **Update test overrides** in test_usage_api_integration.py lines 168, 415 — change `mod._injectable_db_session` to `injectable_session_scope`

### Plan 02
1. **Update 2 tests** in test_langwatch_fetch.py — change `pytest.raises(httpx.HTTPStatusError)` to `pytest.raises(LangWatchInvalidKeyError)` (line 336) and `pytest.raises(LangWatchUnavailableError)` (line 349)

### Plan 04
1. **Update 2 cache key tests** in test_langwatch_caching.py that assert `"all"` scope — update to expect `"user:none"` for non-admin empty set
2. **Make `is_admin` keyword-only** in get_usage_summary signature, specify router call site update: `is_admin=current_user.is_superuser`

### Plan 05
1. **Update LangWatchKeyForm.tsx** `getErrorMessage` to check `error.code` in addition to `error.detail?.code`
2. **Update ErrorState.tsx** `getErrorCode` to handle new error shape (or mark as dead code)
3. **Update LangWatchService.test.ts** assertions from `.toEqual({ detail: ... })` to `.toThrow("...")`

### Plan 06
1. **REDESIGN Task 2** — Flow name→ID keying is UNSAFE. Traces only have names in labels, not IDs. Use `dict[str, list[FlowMeta]]` for name collisions, or filter by allowed_flow_ids to disambiguate
2. **Add test update instructions** for Tasks 3-4: test_langwatch_flow_runs.py, test_langwatch_service_skeleton.py, test_flow_runs_endpoint.py
3. **Don't change line 752** exec→execute — `scalar_one_or_none()` is SQLAlchemy-only, incompatible with SQLModel's `exec`
4. **Add AsyncGenerator import** for get_langwatch_service return type

### Plan 07
1. **Update E2E test** usage-dashboard.spec.ts line 54 — clicks `[data-testid="usage-tab"]` which is being removed
2. **Delete/rewrite unit test** AppHeader.usage-nav.test.tsx — asserts usage-tab link in header
3. **Set ENABLE_USAGE_TRACKING = true** as default (or note that verification requires true)
4. **Wrap loading skeleton** in PageLayout too (UsagePage line 27)
