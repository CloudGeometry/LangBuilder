# Research Notebook: Dashboard Completeness Audit
**Started:** 2026-03-17
**Status:** In Progress
**Classification:** Bug
**Scope:** Codebase only
**Mode:** Deep

## Research Question
Three issues: (1) Zero cost despite real LLM calls — token capture gap. (2) No flow drill-down — FlowBreakdownList exists but not wired. (3) What ELSE is missing from the 41-task implementation?

## Log

### Entry 1 — Baseline
- Usage dashboard shows 5 invocations, 2 flows, $0 cost
- FlowBreakdownList, FlowBreakdownRow, FlowRunsTable components exist but aren't rendered
- Coding report claimed 100% completion (41/41 tasks, 670+ tests)
- We've already found and fixed 20+ bugs — what else is lurking?
