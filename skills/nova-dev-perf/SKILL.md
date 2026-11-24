---
name: nova-dev-perf
description: Performance pass on a change: work done inside loops, repeated reads, N+1 queries, unbounded growth, and slow paths at realistic size. Use for "nova dev perf" or when a change touches a hot path.
---

# Nova Dev Perf

Check the change for:

- **Work inside a loop** that could be done once: repeated file reads, repeated parsing, repeated network calls.
- **N+1 queries:** one query per item in a list. Batch it or join it.
- **Unbounded growth:** lists, caches or files that grow with every request and are never trimmed.
- **Quadratic code:** nested scans over the same data. Use a dict or set.
- **Blocking work** on a request or UI thread.

Estimate at the size the project really sees (ask or read the config for expected rows/requests). Report only problems that matter at that size, each with the measured or reasoned cost, the smallest fix, and the file:line. If you measure, say how. End with Skipped / Risk.
