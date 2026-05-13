# Research Plan: Trace-to-Flow Matching Gap
**Date:** 2026-03-17
**Mode:** Deep
**Threads:** 3

## Scope
Investigate the mismatch between how LangBuilder's tracer sends trace metadata to LangWatch and how the Usage service expects to receive it.

## Threads
| # | Angle | Investigates |
|---|-------|-------------|
| 1 | LangBuilder Tracer | How services/tracing/langwatch.py sets trace metadata, labels, thread_id, flow info |
| 2 | Usage Service Parser | How _filter_by_ownership, _parse_trace, _fetch_from_langwatch filter and match traces |
| 3 | Real Trace Data | What the actual LangWatch API returns, what fields are available to match on |
