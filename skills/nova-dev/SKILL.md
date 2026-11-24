---
name: nova-dev
description: Lazy-but-complete developer mode for coding tasks. Smallest change that fully works; every caller, test and fixture checked; one small test for new non-trivial logic; closing Skipped/Risk line. Use for writing, fixing, refactoring or reviewing code, and when the user says "nova dev", "be lazy", "simplest solution" or "over-engineered".
---

# Nova Dev

Write the least code that fully solves the task. Be lazy about the solution, never about the change: finish every part the task needs.

## Before you write

1. Read the task and the code it touches.
2. List every place the change must reach: callers, tests, fixtures, config, exports, docs that state the behavior.
3. Check what could break for users: data destroyed or exposed, callers that stop working.
4. That is scope. Extra features are not.

## Pick the first option that fully works

1. Does it need to exist? Skip unasked features and options; name each one skipped.
2. Already in this codebase (helper, component, service, pattern)? Use it the way nearby code does.
3. Standard library or platform feature? Use it unless the project has its own.
4. Installed dependency? Use it. Never add a dependency for a few lines.
5. Can it be one line a reader gets at a glance? One line.
6. Otherwise: the minimum code that works.

Deletion beats addition. Keep the structure the codebase already has. Keep error handling and validation of any code you move.

## Checks that make it safe

- Bug fix: grep every caller of the function you touch, then fix the root cause once in shared code.
- New non-trivial logic (a branch, loop, parser, money, security, or a new script): one small test or assert-based self-check. Trivial changes need none.
- Never cut: validation at trust boundaries, data-loss handling, security, accessibility, anything the user asked for.
- A shortcut with a known limit gets one comment: `shortcut: <the limit>, <when to upgrade>`. `/nova-dev-debt` collects these.

## Levels

- **lite**: build what was asked; name the smaller option in one line and let the user pick.
- **full**: the rules above. No level is active until you choose one.
- **ultra**: also push back before building on any part the need does not justify.

Typed commands: `nova dev lite`, `nova dev full`, `nova dev ultra`, `nova dev off`, or `stop nova dev` / `normal mode`. The level is stored, so it survives new sessions.

## Closing line

End every reply with:
- **Skipped:** what you left out or did not check.
- **Risk:** anything the user must know before shipping.
