---
name: nova-dev-logs
description: Shrink a long command output or log to its failing lines and tail. Use for "nova dev logs <file>" or when a test or build log is too long to read.
---

# Nova Dev Logs

Run:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/logsum.py" <log file> 60
```

Report the header line and the failing sections. If the log file does not exist yet, run the command with its output redirected to a file first: `<command> > run.log 2>&1`, then summarize `run.log`.
