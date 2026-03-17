---
skill: serious-plan
slug: dashboard-completeness-fix
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
---

# Phase Map: Cost Tracking Dashboard — FR Completion

## Overview
Fix all 14 Must Have FRs from the Cost Tracking Dashboard PRD. Currently 5 of 14 FRs work (36%). Four micro plans cover: wiring existing dead-code components (5 FRs), fixing token capture ($0 cost), building the missing sub-view toggle (1 FR), and building multi-flow selection (1 FR).

## Plans
| # | Plan | Concern | FRs | Tasks | Risk |
|---|------|---------|-----|-------|------|
| 01 | 01_wire_existing_components.md | Wire FlowBreakdownList, EmptyStatePrompt, ErrorState, UserFilter | FR-003, FR-005, FR-007, FR-008, FR-010 | 6 | M |
| 02 | 02_fix_token_capture.md | Monkey-patch LangWatch callback for Anthropic/streaming tokens | FR-006, FR-014 | 3 | H |
| 03 | 03_build_subview_toggle.md | Build Flows/MCP Server sub-view toggle | FR-002 | 5 | L |
| 04 | 04_build_multi_select.md | Build checkbox multi-selection with summed totals | FR-012 | 6 | M |

**Total: 20 tasks across 4 plans**

## Execution Phases

### Phase 1 — parallel
**Plans:** 01, 02
**Rationale:** Plan 01 modifies UsagePage.tsx (frontend). Plan 02 modifies langwatch.py (backend tracer). Completely different files, no conflicts. Both are P0 — the dashboard is unusable without either.

### Phase 2 — parallel
**Plans:** 03, 04
**Rationale:** Both modify UsagePage.tsx but in different sections. Plan 03 adds a toggle above the filter bar. Plan 04 adds selection state and passes it to FlowBreakdownList. CAUTION: both touch UsagePage.tsx — must merge carefully. Plan 04 depends on Plan 01 (FlowBreakdownList must be wired first).
**Depends on:** Phase 1

### Phase 3 — sequential
**E2E verification:** Full smoke test of all 14 FRs against the running app.
**Depends on:** Phase 2

## Dependency Graph
```
01 (wire components) ──┬──→ 03 (sub-view toggle) ──┐
                       │                             │
                       ├──→ 04 (multi-select)    ────┤──→ E2E verify
                       │                             │
02 (token capture)  ───┘─────────────────────────────┘
```

## File Conflict Analysis
- **Phase 1:** Plan 01 → UsagePage.tsx; Plan 02 → langwatch.py — NO conflict
- **Phase 2:** Plan 03 → UsagePage.tsx + new SubViewToggle.tsx; Plan 04 → UsagePage.tsx + FlowBreakdownList.tsx + new SelectionSummary.tsx — **CAUTION: both touch UsagePage.tsx**. Plan 03 adds toggle in the header area; Plan 04 adds selection state and summary. Different sections but must merge carefully.

## FR Coverage After All Plans Complete

| FR | Plan | Status After |
|---|---|---|
| FR-001 | Already fixed | DONE |
| FR-002 | Plan 03 | DONE |
| FR-003 | Plan 01 | DONE |
| FR-004 | Already working | DONE |
| FR-005 | Plan 01 | DONE |
| FR-006 | Plan 02 | DONE |
| FR-007 | Plan 01 | DONE |
| FR-008 | Plan 01 | DONE |
| FR-009 | Already working | DONE |
| FR-010 | Plan 01 | DONE |
| FR-011 | Already working | DONE |
| FR-012 | Plan 04 | DONE |
| FR-013 | Already working | DONE |
| FR-014 | Plan 02 | DONE |
