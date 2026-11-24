---
name: nova-dev-compact
description: Prepare a session for /compact: capture the state that must survive it, so the restored context is small and correct. Use for "nova dev compact" or when context is large and the task is mid-way.
---

# Nova Dev Compact

The pre-compact hook already saves recent turns to `.claude/CONTEXT-SNAPSHOT.md`, and the restore hook puts a capped copy back after `/compact`. Before the user runs `/compact`:

1. Write a 10-line state note in the reply: the goal, the next step, files touched, open decisions, and the last check result.
2. Tell the user to run `/compact`, then continue from the note.
3. After compaction, check the restored context for that note; if it is missing, use the note itself.

Do not paste the snapshot file into the reply. Do not start new work before the user has compacted.
