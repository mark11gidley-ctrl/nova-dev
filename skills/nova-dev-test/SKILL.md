---
name: nova-dev-test
description: Add the one small test a change needs, matched to the project's existing test framework. Use for "nova dev test" or when new logic has no test.
---

# Nova Dev Test

1. Find the project's test framework and where its tests live (look for `tests/`, `__tests__`, `*_test.*`, `test_*.py`, or a test script in the package file). Use the one already there. Add no new framework.
2. Write one test for the new logic: the normal case and the edge case that would break users (empty input, the boundary, the error path). Do not test the framework.
3. Run only that test. Report the exact command and its result.
4. Run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/testcheck.py"` to confirm a test file is now in the change.

If the project has no test setup, write an assert-based self-check next to the code and say so.
