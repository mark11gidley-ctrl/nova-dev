---
name: nova-dev-bugfix
description: Fix a confirmed bug the disciplined way: grep every caller, fix the root cause once in shared code, add a regression test, and verify. Use for "nova dev bugfix" after a bug is triaged.
---

# Nova Dev Bugfix

1. Confirm the root cause in one sentence (run `nova-dev-triage` if it is not yet clear).
2. `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/callers.py" <function>` for the function you will change. Note every caller and what it expects.
3. Fix the root cause in the shared code, not at each caller. If a caller depends on the old buggy behavior, say so and handle it.
4. Add one regression test that fails before the fix and passes after. Run it, and show both results when you can.
5. Run the project's existing tests for the touched area. Report the command and result.

Report: root cause, files changed, the test, and the callers checked. End with Skipped / Risk.
