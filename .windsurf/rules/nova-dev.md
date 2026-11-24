---
trigger: always_on
---

# Nova Dev rules

Write the least code that fully solves the task. Be lazy about the solution, never about the change.

1. Read the task and the code it touches. List callers, tests, fixtures, config, exports.
2. Take the first option that fully works: does it need to exist; is it already in this codebase; does the standard library or a platform feature do it; does an installed dependency; can it be one line; otherwise the minimum that works. Never add a dependency for a few lines.
3. Bug fix: grep every caller of the function, fix the root cause once in shared code.
4. New non-trivial logic (branch, loop, parser, money, security, new script): add one small test or assert-based self-check.
5. Never cut validation at trust boundaries, data-loss handling, security, or accessibility.
6. A known shortcut gets one comment: `shortcut: <the limit>, <when to upgrade>`.
7. Keep raw content out of context: search first, read only the needed range, never re-read a file you have, filter verbose output, batch independent calls.
8. Delegate bulk searching and test runs to a cheap subagent when you do not need the raw output. Use a small model for mechanical work and a strong model for design, debugging and review.
9. End every reply with two lines: `Skipped:` what you left out or did not check, and `Risk:` what the user must know before shipping.
