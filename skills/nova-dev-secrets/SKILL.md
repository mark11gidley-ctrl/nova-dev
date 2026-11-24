---
name: nova-dev-secrets
description: Scan staged or working changes for secrets (keys, tokens, private key blocks, assigned passwords) without printing the values. Use for "nova dev secrets" or before any commit or push.
---

# Nova Dev Secrets

Scan the staged change, or the working diff if nothing is staged:

```
git diff --cached | python -I "${CLAUDE_PLUGIN_ROOT}/scripts/secret_scan.py"
```

If that prints nothing and nothing is staged, use `git diff HEAD` instead. Report each finding as file:line and kind. Never print the value. If a secret is found, tell the user to rotate it, because it is already in the diff; removing it from the file is not enough once it has been committed.

Exit 0 means clean; exit 1 means a finding.
