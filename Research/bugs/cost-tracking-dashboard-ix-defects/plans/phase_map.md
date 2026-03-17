---
skill: serious-plan
slug: cost-tracking-dashboard-ix-defects
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Phase Map: Cost Tracking Dashboard IX — Bug Fixes

## Overview
19 bugs + 4 navigation defects found during QA review of the Cost Tracking Dashboard IX feature. Decomposed into 7 focused micro plans, executable across 4 phases.

## Plans
| # | Plan | Concern | Tasks | Risk | Bugs |
|---|------|---------|-------|------|------|
| 01 | 01_fix_di_crashes.md | DI crash in router + service | 4 | H | BUG-C1, BUG-C2 |
| 02 | 02_fix_service_crashes.md | Null dates + httpx errors | 4 | H | BUG-C3, BUG-C4, BUG-L3 |
| 03 | 03_fix_migration_and_model.md | SQLite migration + datetime | 4 | M | BUG-L9, BUG-L8 |
| 04 | 04_fix_security_and_cache.md | Cache key collision + Redis | 6 | H | BUG-L4, BUG-L1, BUG-L10, BUG-I1 |
| 05 | 05_fix_frontend_errors.md | Error display in UI | 4 | M | BUG-I2, BUG-I3 |
| 06 | 06_fix_service_cleanup.md | Connection leak + dead code | 6 | M | BUG-L2, BUG-L5, BUG-L6, BUG-L7, STY-1, STY-2 |
| 07 | 07_fix_navigation.md | Usage nav placement | 6 | L | NAV-1, NAV-2, NAV-3, NAV-4 |

**Total: 34 tasks across 7 plans**

## Execution Phases

### Phase 1 — parallel
**Plans:** 01, 03, 07
**Rationale:** Plan 01 fixes the DI crash (unblocks all backend work). Plan 03 fixes the migration (independent — different files). Plan 07 is frontend-only navigation (no backend dependencies). All three touch completely different files.

### Phase 2 — parallel
**Plans:** 02, 04
**Rationale:** Both depend on Plan 01 (DI must work first). Plan 02 fixes service-level crashes. Plan 04 fixes cache/security. They modify different parts of service.py (02 touches fetch methods, 04 touches cache key building).
**Depends on:** Phase 1

### Phase 3 — parallel
**Plans:** 05, 06
**Rationale:** Plan 05 fixes frontend error display (needs working backend from Plans 01+02). Plan 06 cleans up service internals (needs stable DI from Plan 01). Different layers (frontend vs backend).
**Depends on:** Phase 2

### Phase 4 — sequential
**Verification:** End-to-end smoke test of the full feature across all fixes.
**Depends on:** Phase 3

## Dependency Graph
```
01 (DI crash)  ──┬──→ 02 (service crashes) ──┬──→ 05 (frontend errors) ──┐
                 │                             │                           │
                 ├──→ 04 (security/cache)  ────┤──→ 06 (service cleanup) ──┤──→ E2E verify
                 │                             │                           │
03 (migration) ──┘                             └───────────────────────────┘
07 (navigation) ──────────────────────────────────────────────────────────┘
```

## File Conflict Analysis
No two plans in the same phase modify the same files:
- **Phase 1:** Plan 01 → router.py, service.py; Plan 03 → migration, global_settings.py; Plan 07 → appHeaderComponent, AccountMenu, feature-flags, UsagePage
- **Phase 2:** Plan 02 → service.py (fetch methods); Plan 04 → service.py (cache methods), router.py (org_id), schemas.py — **CAUTION:** Both touch service.py but different sections. Must merge carefully.
- **Phase 3:** Plan 05 → LangWatchService.ts, UsagePage.tsx; Plan 06 → service.py (cleanup)
