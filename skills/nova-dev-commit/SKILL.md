---
name: nova-dev-commit
description: Write a clear commit message from the staged change: a short subject, a body that says why, and the attribution line the environment requires. Use for "nova dev commit" or before committing.
---

# Nova Dev Commit

1. Read the staged change: `git diff --staged --stat`, then the diff for the files that matter.
2. Subject: under 72 characters, imperative mood, says what changed ("Reject empty webhook URL").
3. Body: why the change is needed, and anything a reviewer must know (skipped items, risk). Wrap at 72 characters. No marketing words.
4. Add the attribution line the environment specifies, if any. Do not invent one.
5. Show the message to the user. Commit only if the user asks.

Do not include secrets, file contents, or long lists of every file.
