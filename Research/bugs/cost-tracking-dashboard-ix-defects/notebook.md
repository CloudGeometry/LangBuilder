# Research Notebook: Cost Tracking Dashboard IX Defects
**Started:** 2026-03-17
**Status:** In Progress
**Classification:** Bug
**Scope:** Codebase only
**Mode:** Deep

## Research Question
Two defects found during QA review of Cost Tracking Dashboard IX:
1. REVIEW-001: Usage link placement — header only, not in sidebar. Is this correct?
2. REVIEW-002: All usage API endpoints crash with async_generator context manager error.

Additionally: are there OTHER bugs lurking in the usage router code?

---

## Log

### Entry 1 — 2026-03-17 Pre-research baseline
**Baseline state:**
- LangBuilder running from AIx workspace on port 18002 (backend) / 13000 (frontend)
- Usage link visible in AppHeader top-right
- Clicking Usage link navigates to /usage
- /usage page renders but shows "Failed to load usage data — An error occurred"
- API calls to /api/v1/usage/ return: `{"message":"'async_generator' object does not support the asynchronous context manager protocol"}`
- API calls to /api/v1/usage/settings/langwatch-key/status return same error
- The error comes from router.py:47-52 where _injectable_db_session wraps injectable_session_scope() with "async with"

### Entry 2 — Initial code locations identified
**Key files in AIx workspace:**
- Router: `src/backend/base/langflow/api/v1/usage/router.py`
- Service: `src/backend/base/langflow/services/langwatch/service.py`
- Schemas: `src/backend/base/langflow/services/langwatch/schemas.py`
- Exceptions: `src/backend/base/langflow/services/langwatch/exceptions.py`
- Session deps: `src/lfx/src/lfx/services/deps.py` (injectable_session_scope at line 149)
- AppHeader: `src/frontend/src/components/core/appHeaderComponent/index.tsx`
- Sidebar: `src/frontend/src/components/core/folderSidebarComponent/components/sideBarFolderButtons/index.tsx`
- DashboardWrapperPage: `src/frontend/src/pages/DashboardWrapperPage/index.tsx`
- Routes: `src/frontend/src/routes.tsx`
