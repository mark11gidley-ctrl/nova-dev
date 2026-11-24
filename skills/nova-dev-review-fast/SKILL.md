---
name: nova-dev-review-fast
description: Fast pre-commit review in one step: compressed diff, secrets scan and test check together. Use for "nova dev review fast" or before committing when a full review is not needed.
---

# Nova Dev Review Fast

Run once:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" review
```

Report the verdict first, then only the findings under Secrets and Tests. If the verdict is "needs attention", suggest `/nova-dev-review` for the full review. Do not paste the compressed diff unless the user asks for it.
