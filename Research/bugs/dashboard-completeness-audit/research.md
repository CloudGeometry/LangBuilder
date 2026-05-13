---
skill: serious-research
slug: dashboard-completeness-audit
status: done
parent:
created: 2026-03-17
classification: Bug
scope: Codebase only
mode: Deep
---

# Cost Tracking Dashboard — Completeness Audit

## Summary

The coding report's claim of "41/41 tasks, 670+ tests, zero gaps" is materially false. Systematic cross-reference of all 14 Must Have FRs from the PRD against the running application reveals: 5 FRs working, 4 built but not wired, 1 partially broken, 2 completely missing, plus a fundamental token capture bug that makes all cost data $0.00.

## FR Compliance Matrix

| FR | Requirement | Built? | Wired? | Status |
|---|---|---|---|---|
| FR-001 | Usage tab in navigation | YES | YES | **FIXED** (Account Menu) |
| FR-002 | Sub-view toggle (Flows / MCP Server) | **NO** | NO | **MISSING** — no toggle component exists |
| FR-003 | First-visit API key prompt (admin vs user) | YES (EmptyStatePrompt has `isAdmin` prop) | **NO** (inline div, no admin/user distinction) | **NOT WIRED** |
| FR-004 | API key validation & encrypted storage | YES | YES | **WORKING** |
| FR-005 | API key error handling | YES (ErrorState + LangWatchKeyForm) | **NO** (inline div, no retry button) | **NOT WIRED** |
| FR-006 | Aggregate summary card | YES | YES | **WORKING** (but $0 cost — see Finding 1) |
| FR-007 | Per-flow breakdown list | YES (FlowBreakdownList) | **NO** | **NOT WIRED** — `data.flows` ignored |
| FR-008 | Expandable per-flow run detail | YES (FlowRunsTable) | **NO** | **NOT WIRED** |
| FR-009 | Date range picker | YES | YES | **WORKING** |
| FR-010 | Admin user filter | YES (UserFilterDropdown) | **PARTIAL** (`users={[]}` hardcoded) | **BROKEN** — always empty |
| FR-011 | Role-based visibility (server-side) | YES | YES | **WORKING** |
| FR-012 | Multi-flow selection with summed totals | **NO** | NO | **MISSING** — no checkbox/selection logic exists |
| FR-013 | Loading states | YES | YES | **WORKING** |
| FR-014 | LangWatch API data sourcing | YES | YES | **WORKING** (but $0 cost) |

**Score: 5 of 14 FRs fully working (36%)**

## Findings

### Finding 1: Token Capture Is Completely Broken (Zero Cost)

**Affects:** FR-006, FR-007, FR-008, FR-014 — all cost figures are $0.00

**Root cause:** Three-part failure in the LangWatch SDK's LangChain callback:

1. **Key name mismatch:** SDK checks `response.llm_output["token_usage"]` — Anthropic uses `"usage"` with `input_tokens`/`output_tokens`
2. **Streaming path dominant:** LangBuilder's Agent always uses `astream_events()`, which produces `llm_output = None`. The entire token extraction block is skipped.
3. **`usage_metadata` never read:** LangChain puts tokens on `message.usage_metadata` for all providers (including streaming), but the SDK never checks it.

**Evidence:** LangWatch API spans show `"metrics": {}` for LLM spans despite successful I/O capture. Our `NativeTracer` callback (`native_callback.py`) has comprehensive 4-location fallback logic — the LangWatch callback checks only 1.

**Fix:** Monkey-patch `get_langchain_callback()` in `langwatch.py` to wrap `on_llm_end` with multi-provider token extraction. Call original first, then inject tokens only if still empty (true fallback, not pre-empt).

**File:** `src/backend/base/langflow/services/tracing/langwatch.py`

### Finding 2: Five Components Built But Not Wired (FR-003, FR-005, FR-007, FR-008)

| Component | Built? | Tested? | Rendered in UsagePage? |
|-----------|--------|---------|----------------------|
| FlowBreakdownList | YES | YES (7 tests) | **NO** |
| FlowBreakdownRow | YES | YES | **NO** |
| FlowRunsTable | YES | YES (7 tests) | **NO** |
| EmptyStatePrompt | YES | YES (7 tests, has `isAdmin` prop for FR-003) | **NO** |
| ErrorState | YES | YES (7 tests, has retry button for FR-005) | **NO** |

UsagePage uses inline `<div>` elements instead. The inline empty state says "configure your API key" even when the key IS configured but there's no data — actively misleading.

**Fix:** Import and render these components. EmptyStatePrompt needs `isAdmin` prop (requires auth context). FlowBreakdownList needs `data.flows`. ErrorState needs retry callback.

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

### Finding 3: FR-002 Sub-View Toggle Completely Missing

The PRD requires a toggle between "Flows" and "MCP Server" usage views. No toggle component exists anywhere in the UsagePage directory. The backend `sub_view` query parameter exists (`UsageQueryParams.sub_view` accepts `"flows"` or `"mcp"`) but the frontend has no UI to switch between them.

**Fix:** Build a toggle component and pass `sub_view` to the API query.

### Finding 4: FR-012 Multi-Flow Selection Completely Missing

The PRD requires checkboxes on flow rows for multi-selection with summed totals. FlowBreakdownList has no checkbox/selection logic. No selection state, no summed totals display.

**Fix:** Add selection state to FlowBreakdownList, add selection summary component.

### Finding 5: FR-010 UserFilterDropdown Hardcoded Empty

Rendered with `users={[]}` on UsagePage line 102-106. Always shows "All users" with no options. The API response has `owner_user_id`/`owner_username` per flow that could populate it. Also missing: admin-only visibility (FR-010 says regular users should NOT see the filter).

**Fix:** Derive user list from `data.flows`. Show only for admins. Hide when <2 users.

### Finding 6: FR-003 No Admin vs User Distinction

The PRD requires:
- Admin with no key: sees setup prompt with input field
- Regular user with no key: sees "Please ask your admin to set up the LangWatch API key"

EmptyStatePrompt component HAS this logic (`isAdmin` prop), but UsagePage doesn't use it — it renders an inline div with no admin/user distinction.

**Fix:** Use EmptyStatePrompt with `isAdmin` from auth store.

### Finding 7: Backend Test Infrastructure Is Broken

| Category | Tests | Status |
|----------|-------|--------|
| Passing | 199 | OK |
| Missing `pytest-httpx` | 32 | ERROR |
| Import failures (MagicMock stubs) | 68 | FAIL |
| Stale mocks (GET→POST) | 4 | FAIL |
| Stale stubs | 4 | FAIL |
| **Total** | **307** | **64% pass rate** |

### Finding 8: useGetKeyStatus Hook Unused

Built, tested, calls `/api/v1/usage/settings/langwatch-key/status`, but never imported. Could provide pre-flight check for FR-003 (show setup prompt vs dashboard).

### Finding 9: Three Dead Exception Classes

`LangWatchTimeoutError`, `LangWatchInsufficientCreditsError`, `LangWatchKeyNotConfiguredError` defined but never raised.

## Sync Pairs

| Function A | Function B | Must agree on |
|-----------|-----------|---------------|
| `_parse_trace` span token extraction | LangWatch SDK `on_llm_end` token writing | Where tokens live |
| `UsagePage` error display | `ErrorState` component | Error object shape |
| `UsagePage` empty state | `EmptyStatePrompt` component | `isAdmin` + variant |
| `FlowBreakdownList` props | `UsageResponse.flows` shape | Flow data structure |
| `UserFilterDropdown` `users` prop | `UsageResponse.flows[].owner_*` fields | User list derivation |
| Backend `sub_view` param | Frontend toggle state | "flows" vs "mcp" string |

## Recommendations — Prioritized by FR

### P0 — Core dashboard broken (FR-007, FR-008, FR-003, FR-005)
1. **Wire FlowBreakdownList + FlowRunsTable** into UsagePage — `data.flows` is available, components are built
2. **Wire EmptyStatePrompt** with `isAdmin` prop for FR-003 admin/user distinction
3. **Wire ErrorState** with retry callback for FR-005

### P0 — Cost data is zero (FR-006, FR-014)
4. **Fix token capture** — monkey-patch `on_llm_end` for multi-provider token extraction

### P1 — Missing FRs
5. **Build FR-002 sub-view toggle** — Flows/MCP Server toggle, pass `sub_view` to API
6. **Build FR-012 multi-flow selection** — checkboxes + summed totals

### P1 — Partially broken
7. **Fix FR-010 UserFilterDropdown** — derive users from `data.flows`, admin-only visibility

### P2 — Test infrastructure
8. Install `pytest-httpx`, fix import chain, update stale mocks/stubs

### P3 — Polish
9. Wire `useGetKeyStatus` for pre-flight check
10. Connect dead exception classes
11. Add truncation/cache indicators

## References

All paths relative to: `/Users/cg-adubuc/cg-ai-msl-workspaces/.../main/langbuilder/`

| Source | Path |
|--------|------|
| **PRD** | `.cg-aix-sdlc/reqs/9ec41dfe-.../PRD.md` |
| **Functional Requirements** | `.cg-aix-sdlc/reqs/9ec41dfe-.../04d-functional-requirements.md` |
| **User Journeys** | `.cg-aix-sdlc/reqs/9ec41dfe-.../04c-user-journeys.md` |
| **Coding Report** | `.cg-aix-sdlc/code/9ec41dfe-.../CODING-REPORT.md` |
| UsagePage | `src/frontend/src/pages/UsagePage/UsagePage.tsx` |
| LangWatch tracer | `src/backend/base/langflow/services/tracing/langwatch.py` |
| Usage service | `src/backend/base/langflow/services/langwatch/service.py` |

### Thread files
- `thread-1-zero-cost.md` — Token capture 3-bug chain
- `thread-2-missing-ui.md` — 5 dead-code components
- `thread-3-backend-audit.md` — 110 test failures
- `thread-4-frontend-audit.md` — 34 tests verify dead code

### Persona reviews
- **Senior Engineer** — Confirmed token analysis, flagged test failures as P0
- **UX Specialist** — Dashboard at 20% utility, minimum viable fix is ~28 lines for wiring
