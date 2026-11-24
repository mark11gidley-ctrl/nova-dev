---
name: nova-dev-handoff
description: Write a short handoff brief so a fresh session (or a subagent) can continue the work without the full history. Use for "nova dev handoff", before /clear, or before starting a new session.
---

# Nova Dev Handoff

Write the brief to `.claude/HANDOFF.md` in the project, under 60 lines:

1. **Goal:** the task in one sentence, as the user stated it.
2. **Done:** files changed, with file:line, and what each change does.
3. **Decided:** choices made and why, so they are not reopened.
4. **Open:** what remains, in order, and the first command to run.
5. **Checks:** the test or check command, and its last result.
6. **Do not:** constraints the user set (scope, files to leave alone).

Keep it factual. No code dumps; reference paths instead. Tell the user the file path and the one-line command to start the next session with it, for example: "Read .claude/HANDOFF.md and continue from Open."
