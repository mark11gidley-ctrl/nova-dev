---
name: nova-dev-review
description: Review a change like the senior dev who gets paged when it breaks. Finds bugs, security holes, real-load problems, risky code without tests, slow paths, and code to cut. Accepts a target: uncommitted, staged, a branch, or a PR. Use for "review", "nova dev review", or before committing.
---

# Nova Dev Review

Choose the target from the user's words:

| Target | Command |
|--------|---------|
| uncommitted (default) | `git diff HEAD` |
| staged | `git diff --staged` |
| branch | `git diff <base>...HEAD` (base is the default branch) |
| PR link or number | `gh pr diff <number>` |

Read the files the diff touches, not only the diff: a rename can break an untouched caller.

For each finding, give:
1. **Where:** file:line
2. **What the code does:** one sentence
3. **What goes wrong:** the concrete failure and the input that triggers it
4. **Fix:** the smallest change
5. **If skipped:** what happens to users

Rank by severity: **Must fix** (breaks users, data loss, security), **Should fix** (missing test on risky logic, slow path under real load), **Cut** (code the change does not need).

Check in order: broken callers and exports; validation at trust boundaries; error handling that prevents data loss; new logic with no test; shared state and concurrency; performance at realistic size.

If nothing is wrong, say so in one line and name what you did not check. Do not invent findings.

End with the Skipped / Risk line.
