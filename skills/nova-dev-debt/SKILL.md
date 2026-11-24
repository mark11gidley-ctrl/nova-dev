---
name: nova-dev-debt
description: List every deferred shortcut in the repo as a ledger, so "later" does not become "never". Accepts a custom marker word. Changes nothing. Use for "nova dev debt", "what did we defer", or "list the shortcuts".
---

# Nova Dev Debt

Run from the repo root (replace `${CLAUDE_PLUGIN_ROOT}` with the plugin folder if it is not set):

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/debt.py" [root] [word]
```

`word` defaults to `shortcut`. If the user's project uses another word, pass it. `ponytail:` markers are always included.

Present the output as a table sorted by file: location, deferred limit, and upgrade trigger. Mark any item whose trigger has already happened as **Due**. Do not edit any file.
