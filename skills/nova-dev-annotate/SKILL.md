---
name: nova-dev-annotate
description: Add short explanatory comments and docstrings to code that needs them: the why, the rules it enforces, and the traps. Never restates the code. Use for "nova dev annotate <file or folder>", "explain this code in the code", or "add comments".
---

# Nova Dev Annotate

Find the targets first:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" annotate <file or folder>
```

Then, for each target, read the function fully before writing anything. Then:

1. **Explain what the code cannot show:** why it exists, the rule it enforces, what callers must pass, the trap a future editor would fall into. One to three short sentences.
2. **Use the file's own style:** the file's docstring format if it has one (Python: a docstring under the `def`; JS/TS/Go/Rust/Java: the comment form the file already uses). Keep the file's language.
3. **Do not:**
   - restate the code ("increments i")
   - explain obvious lines or trivial functions (two to three lines or less)
   - document a behavior you have not verified by reading the callers and running the tests
   - change any code, names or formatting besides comments and docstrings
4. **Mark uncertainty.** If you cannot tell why the code is written a certain way, write `Why unclear: <what you checked>` instead of guessing.
5. **Verify.** Run the project's tests (`/nova-dev-check`) after the change. Comments must not break the build (for example a docstring-only edit can break a doc test).

Report the files changed, how many explanations were added, and the targets you left alone with the reason. End with Skipped / Risk.
