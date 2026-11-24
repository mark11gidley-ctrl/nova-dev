---
name: nova-dev-plan
description: Before coding, write a minimal plan: the change, every caller and test it reaches, what is skipped, and the risk. Use for "nova dev plan" or any task that touches more than one file.
---

# Nova Dev Plan

Write the plan in under 15 lines, then wait for a go-ahead only if the user asked for one:

1. **Change:** one sentence.
2. **Reaches:** every file, caller, test, fixture and doc the change touches. Run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/callers.py" <symbol>` for each symbol you alter.
3. **Smallest option:** the first rung that works (exists already, standard library, installed dependency, one line, minimum code).
4. **Skipped:** features or options nobody asked for.
5. **Test:** the one small test or check for any new logic.
6. **Risk:** what could break for users, data, or security.

Then do the work.
