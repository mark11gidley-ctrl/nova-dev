---
name: nova-dev-settings
description: Show or change nova-dev settings in the config file: level, context warning, window, auto-compact, ledger, webhook, big-read limit. Use for "nova dev settings", "nova dev status", or "change the context warning to X".
---

# Nova Dev Settings

Show the current values and where each comes from:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" status
```

To change a value, edit `config.json` in the state folder (`~/.config/nova-dev/`, or `NOVA_DEV_DIR`). Example:

```json
{"context_warn": 120000, "autocompact": false, "big_read": 800}
```

Environment variables override the file. Keys: `level`, `context_warn`, `window`, `autocompact`, `ledger`, `webhook_url`, `webhook_token`, `send_names`, `big_read`.

Never print or paste `webhook_token`; `status` reports it as set or not set. Confirm with the user before enabling `webhook_url`, because it sends each session row off this machine.
