---
name: nova-dev-docs
description: Find and fix documentation that a change made wrong: README sections, usage examples, config tables, and help text. Use for "nova dev docs" or after a behavior change.
---

# Nova Dev Docs

1. List what the change altered: commands, flags, config keys, defaults, output format.
2. Search the docs for each old name or value: `grep` the README, `docs/`, help text, examples and comments.
3. Update each stale line with the smallest edit. Do not rewrite sections that are still correct.
4. Do not add new documentation nobody asked for. Report anything you could not update and why.

End with the list of files changed, or say that no docs referred to the change.
