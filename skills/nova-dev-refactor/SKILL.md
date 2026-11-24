---
name: nova-dev-refactor
description: Shrink code without changing behavior: delete dead code, merge duplicates, use existing helpers. Deletion first. Use for "nova dev refactor" or "make this smaller".
---

# Nova Dev Refactor

Order of work, stopping as soon as the code is small enough:

1. Find dead code: functions with no callers (`callers.py`), unused imports, commented-out blocks. Delete them.
2. Find duplicates: the same logic in two places. Keep the one that already has tests; point the other at it.
3. Find the helper the codebase already has for the job. Replace the hand-written version.
4. Flatten: remove wrappers and layers that only forward a call.

Rules: behavior does not change; error handling and validation move with the code; run the existing tests before and after; report lines removed and lines added. Do not rename public names unless every caller is updated in the same change.
