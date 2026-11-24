---
name: nova-dev-band
description: Band tools for nova-dev: the task ledger, past-session import, the last task as Markdown, the HTML board, and the statusline setup. Use for "nova dev band", "import my sessions", "show my tasks", "open the board", "copy the last task", or "set up the statusline".
---

# Nova Dev Band

Run the matching command (replace `${CLAUDE_PLUGIN_ROOT}` with the plugin folder if it is not set):

| User asks | Run |
|-----------|-----|
| Import past sessions into the board | `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/band.py" import` |
| Last task as Markdown | `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/band.py" last` |
| Tasks in the last N days | `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/band.py" show N` |
| Open the board | `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/band.py" board`, then open the printed path |

Ledger rows are written after every turn (Stop hook) to `~/.config/nova-dev/band/<project>.csv`. Turn that off with `NOVA_DEV_LEDGER=0`.

Webhook (off by default): set `NOVA_DEV_WEBHOOK_URL` to an https address to receive each task's row as JSON. Optional `NOVA_DEV_WEBHOOK_TOKEN` is sent as a Bearer token. Set `NOVA_DEV_SEND_NAMES=0` to leave task names out. Only set this if you trust the receiver.

Statusline (shows context size and last test result): Claude Code's statusline is set in its settings file, which a plugin cannot change. Add this to your settings, then restart Claude Code:

```json
"statusLine": { "type": "command", "command": "python -I \"C:/claudeobsidainai/nova-dev/hooks/statusline.py\"" }
```

Band buttons from the other plugin (switch level, run review, copy task, fold to one line) need the Claude Code interface, which a plugin cannot add. Use the matching commands instead: `nova dev lite|full|ultra`, `/nova-dev-review`, `band.py last`, and the statusline setting above.
