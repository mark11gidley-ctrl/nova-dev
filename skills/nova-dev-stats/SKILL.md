---
name: nova-dev-stats
description: Show measured token use and cache hit rate from your own Claude Code transcripts, over a chosen number of days. Real numbers, not estimates. Use for "nova dev stats", "how many tokens did I use", or "what is my cache hit rate".
---

# Nova Dev Stats

Run from anywhere:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/stats.py" 30
```

Pass another day count in place of 30 if the user asks for a different window. If `${CLAUDE_PLUGIN_ROOT}` is not set, locate the `nova-dev` plugin folder.

Show the output as-is, then add two plain sentences: what the cache hit rate means (higher is cheaper, because cached reads cost far less than fresh input), and the single biggest lever for this window (usually: long sessions that keep growing, or repeated full-file reads). Do not estimate dollar cost; the script reports tokens only.
