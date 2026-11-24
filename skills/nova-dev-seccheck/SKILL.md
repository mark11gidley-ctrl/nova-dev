---
name: nova-dev-seccheck
description: Audit the nova-dev plugin's own code for dangerous calls (shell injection, eval, unsafe pickle or yaml, disabled TLS, plain http, hardcoded credentials). Use for "nova dev seccheck" or after changing any plugin script.
---

# Nova Dev Seccheck

Run:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" seccheck
```

Report each finding as file:line and rule. For each one, say whether it is a real risk or a deliberate use; only real risks need a fix. Do not add an allow-list entry without a stated reason in `scripts/seccheck.py`. End with the Skipped / Risk line.
