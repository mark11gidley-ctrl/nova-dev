---
name: nova-dev-find
description: Find a past session by something you asked in it. Searches your own prompts across all transcripts, newest first. Use for "nova dev find <words>", "where did we fix X", or "which session was about Y".
---

# Nova Dev Find

Run:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" find <words>
```

Show the matches as: date, session id, project, and the snippet. If the user wants to continue one, give them `claude --resume <session id>`. Only your prompts are searched; assistant replies are not.
