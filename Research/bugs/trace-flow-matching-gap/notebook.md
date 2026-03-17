# Research Notebook: Trace-to-Flow Matching Gap
**Started:** 2026-03-17
**Status:** In Progress
**Classification:** Bug
**Scope:** Codebase only
**Mode:** Deep

## Research Question
Why does the Usage dashboard show zero data when LangWatch traces exist? The gap is between what the LangBuilder tracer sends and what the Usage service expects.

## Known facts
- Direct LangWatch API call returns 2 traces with `labels: []`, `thread_id: None`, `metadata: {telemetry.sdk.*}`
- Usage service `_filter_by_ownership` looks for `"Flow: <name>"` in labels
- No labels = no matches = zero results

## Log

### Entry 1 — Baseline
Traces confirmed via curl to LangWatch API. Empty labels, no flow identification metadata.
