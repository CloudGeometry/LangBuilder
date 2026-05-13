---
skill: serious-review
slug: cost-tracking-dashboard-ix
status: active
parent:
created: 2026-03-17
reviewing: Cost Tracking Dashboard IX — 41-task feature (5 features, 670+ tests) per coding report 9ec41dfe
---

# Review Findings: Cost Tracking Dashboard IX

---

## Build Gate
- **Status:** Pending — investigating runtime behavior
- **Backend:** Starts, /api/v1/usage/ returns 403 (endpoint exists, auth required)
- **Frontend:** Starts, serves HTTP 200

---

## Issues

### REVIEW-001: Usage link visible but not in sidebar — REVISED to Medium
- **Type:** UX
- **Severity:** Medium
- **Location:** `src/components/core/appHeaderComponent/index.tsx:86-92`
- **Description:** Usage link is in the AppHeader (top-right), which renders on all authenticated pages including `/flows`. Link is visible and clickable. However, it's not in the sidebar alongside Knowledge/My Files, which is where users might look for top-level sections.
- **Expected:** Usage discoverable from both header and sidebar
- **Actual:** Only in header (top-right). Functionally accessible but could be missed by users.
- **Note:** Original report was wrong — AppHeader renders on all pages via DashboardWrapperPage, not just flow editor.

### REVIEW-003: Usage empty state not centered vertically/horizontally
- **Type:** UX
- **Severity:** Low
- **Location:** `src/frontend/src/pages/UsagePage/UsagePage.tsx` — the "No API Key Configured" empty state
- **Description:** The "No API Key Configured" / "Configure your LangWatch API key" message is not vertically or horizontally centered in the available viewport area. It appears offset toward the bottom-left.
- **Expected:** Centered both vertically and horizontally within the content area (below the PageLayout header)
- **Actual:** Text sits at roughly the vertical midpoint but is not properly centered with flexbox

### REVIEW-002: Usage API crashes — async generator used as context manager
- **Type:** Bug
- **Severity:** Critical
- **Location:** `langflow/api/v1/usage/router.py:47-52`
- **Description:** All usage API endpoints crash with `'async_generator' object does not support the asynchronous context manager protocol'`. The `_injectable_db_session()` dependency wraps `injectable_session_scope()` with `async with`, but `injectable_session_scope()` (lfx/services/deps.py:149-151) is an async generator (uses `yield`), not an async context manager. FastAPI handles async generators as dependencies natively — they should not be wrapped in `async with`.
- **Expected:** `/api/v1/usage/` returns usage data; `/api/v1/usage/settings/langwatch-key/status` returns key status
- **Actual:** Both return `{"message":"'async_generator' object does not support the asynchronous context manager protocol"}`
- **Root cause:** `router.py:51` does `async with injectable_session_scope() as session:` but `injectable_session_scope` is an async generator, not decorated with `@asynccontextmanager`
- **Fix:** Either use `injectable_session_scope` directly as the FastAPI dependency (remove the wrapper), or change the wrapper to `async for session in injectable_session_scope(): yield session`
- **Impact:** Blocks ALL usage endpoints — the entire Cost Tracking Dashboard is non-functional
