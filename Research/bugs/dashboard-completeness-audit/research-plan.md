# Research Plan: Dashboard Completeness Audit
**Date:** 2026-03-17
**Mode:** Deep
**Threads:** 4

## Scope
Full audit of the Cost Tracking Dashboard implementation against the coding report, PRD, and spec.

## Threads
| # | Angle | Investigates |
|---|-------|-------------|
| 1 | Zero Cost Root Cause | Why tokens/cost are null — trace the full token capture path from LLM response through tracer to LangWatch to Usage service |
| 2 | Missing UI Components | What frontend components exist but aren't wired — FlowBreakdownList, FlowRunsTable, etc. |
| 3 | Backend Completeness Audit | Compare every backend file against the coding report's task list — what's actually implemented vs what's a stub |
| 4 | Frontend Completeness Audit | Compare every frontend component/hook/test against the coding report — what renders vs what's dead code |
