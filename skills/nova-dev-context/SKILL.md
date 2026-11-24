---
name: nova-dev-context
description: Show how large this session's context is, how it grew turn by turn, and whether to compact, clear, or start fresh. Use for "nova dev context", "how full is my context", or "should I compact".
---

# Nova Dev Context

1. Find this session's transcript: the newest `.jsonl` under `~/.claude/projects/<this project folder>/`.
2. Run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/contexthist.py" <transcript>`.
3. Report: the latest context size, the peak, the window (`NOVA_DEV_WINDOW`, default 200,000), and the turns marked `jump`.
4. Recommend one action:
   - under 50% of the window: keep going.
   - 50% to 75%: finish the current task, then `/compact`.
   - above 75%, or a new unrelated task: `/clear` or a new session, with `nova dev handoff` first.

Measured numbers only. Do not guess token counts from message length.
