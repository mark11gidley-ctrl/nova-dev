---
name: nova-dev-check
description: Run the project's own test, lint and build commands and report only what failed, with file:line. Use for "nova dev check" or before calling a change done.
---

# Nova Dev Check

1. Find the project's commands: the test, lint, and build scripts in the package file, Makefile, or CI config (`.github/workflows/`). Use what the project already defines.
2. Run each one, redirecting long output to a file (for example `npm test > check.log 2>&1`). Do not paste full logs.
3. Report, for each command: exit code, pass and fail counts, and every failure's name, assertion, and file:line (grep the log for `FAIL`, `Error`, `failed`).
4. Also run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/testcheck.py"` to confirm a test file changed with the logic.

If a command is missing, say which one and do not invent it. End with Skipped / Risk.
