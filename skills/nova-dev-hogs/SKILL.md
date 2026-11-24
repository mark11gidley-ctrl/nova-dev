---
name: nova-dev-hogs
description: Find what fills the context: tool outputs by size, and files read more than once in a session. Use for "nova dev hogs", "what is using my context", or "what do I keep re-reading".
---

# Nova Dev Hogs

1. Find this session's transcript (newest `.jsonl` under `~/.claude/projects/<project folder>/`).
2. Run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/toolcost.py" <transcript> 10`.
3. Report the top tools by output size and every file read more than once.
4. For each hog, one fix:
   - a big Bash output: pipe through `tail`, `grep -c`, or `scripts/logsum.py` next time.
   - a big file read: run `scripts/outline.py` first, then Read a range.
   - a repeated read: keep the earlier result; the read guard already blocks unchanged re-reads.

Measured sizes only. Do not change any file.
