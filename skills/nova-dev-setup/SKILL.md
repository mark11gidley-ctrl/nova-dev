---
name: nova-dev-setup
description: Check for and install what nova-dev needs (Python, Git, Node.js, ffmpeg, Codex CLI) using the system package manager. Asks before installing each item. Use for "nova dev setup", "install what nova dev needs", or when hooks fail for a missing program.
---

# Nova Dev Setup

1. Show what is missing (no install yet):

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" setup
```

2. Tell the user the list, and the command for each item. Ask which items to install. Do not use `--yes` unless the user says yes to all of them.
3. For each item the user approves, run the install. Commands come from the script's output, so run exactly what it printed for that item.
4. Afterwards, tell the user to open a new terminal so the new programs are on PATH, then run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`.

Installs change the system, so never run them without the user's approval. End with Skipped / Risk.
