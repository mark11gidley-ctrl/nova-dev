---
name: nova-dev-outline
description: Outline a long file (definitions and headings with line numbers) so only the needed range is read. Use for "nova dev outline <file>" or before reading any file longer than about 300 lines.
---

# Nova Dev Outline

Run:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/outline.py" <file>
```

Then Read only the range that matters, with offset and limit set to the lines the outline gives. Report the outline to the user if they asked for it; otherwise use it silently.
