---
name: nova-dev-help
description: Quick reference for nova-dev commands, levels and what each hook does. Use for "nova dev help" or when unsure which nova-dev command to run.
---

# Nova Dev Help

| Command | What it does |
|---------|--------------|
| `nova dev lite` / `full` / `ultra` | Set the level. Stored, so it persists. |
| `nova dev off` or `normal mode` | Turn everything off, token guards included. |
| `stop nova dev` | Same as `off`. |
| `/nova-dev-review` | Review the current change: bugs, security, load, tests, what to cut. |
| `/nova-dev-audit` | Review the whole repo; ranked, fix-first list. |
| `/nova-dev-debt` | Ledger of deferred `shortcut:` comments. |
| `/nova-dev-stats` | Measured tokens and cache hit rate from your transcripts. Add `--top 5` to see the most expensive sessions. |
| `/nova-dev-route` | Model routing rules for subagents. |
| `/nova-dev-band` | Ledger, import of past sessions, last task as Markdown, HTML board, statusline setup, webhook. |
| `/nova-dev-plan` | Minimal plan with every caller and test the change reaches. |
| `/nova-dev-test` | Add the one small test a change needs. |
| `/nova-dev-refactor` | Shrink code without changing behavior. Deletion first. |
| `/nova-dev-security` | Security pass: validation, injection, secrets, auth, paths. |
| `/nova-dev-perf` | Performance pass on hot paths at realistic size. |
| `/nova-dev-a11y` | Accessibility check for UI changes. |
| `/nova-dev-deps` | Dependency review: thin, unused, duplicate, risky packages. |
| `/nova-dev-explain` | Plain-language explanation of code, with callers and failure modes. |
| `/nova-dev-commit` | Commit message from the staged change. |
| `/nova-dev-pr` | Pull request description that follows the repo's template. |
| `/nova-dev-docs` | Find and fix docs a change made wrong. |
| `/nova-dev-changelog` | One changelog entry in the project's format. |
| `/nova-dev-triage` | Reproduce, locate, rank and fix-plan a bug report. |
| `/nova-dev-bugfix` | Root-cause fix with callers checked and a regression test. |
| `/nova-dev-scope` | Challenge a request and offer the smaller version. |
| `/nova-dev-check` | Run the project's tests, lint and build; report failures only. |
| `/nova-dev-context` | Context size per turn, jumps, and whether to compact, clear or start fresh. |
| `/nova-dev-hogs` | Tool output by size, and files read more than once. |
| `/nova-dev-handoff` | Brief for a fresh session, written to `.claude/HANDOFF.md`. |
| `/nova-dev-compact` | Prepare state before `/compact`, so the restored context is small and correct. |
| `/nova-dev-init` | Per-project setup: level file and git ignores. Never overwrites. |
| `/nova-dev-outline` | Outline a long file so only needed ranges are read. |
| `/nova-dev-logs` | Shrink a long log to its failing lines and tail. |
| `/nova-dev-secrets` | Scan the diff for secrets; never prints values. |
| `/nova-dev-annotate` | Add short explanations to code: the why, the rules, the traps. Never restates code. |
| `/nova-dev-help` | This page. |

**Context features:** after `/compact`, the snapshot is restored (capped at 6,000 characters). `NOVA_DEV_BIG_READ=<lines>` blocks whole-file reads of longer files (off by default). `scripts/init.py`, `contexthist.py`, `toolcost.py`, `outline.py`, `logsum.py`, `diffcompress.py` and `secret_scan.py` are the measured tools behind these skills.

**Scripts:** `callers.py <symbol>` lists every use; `testcheck.py` flags logic added without a test; `stats.py 30 --by-project` breaks tokens down by project; `band.py export json|csv` exports the ledger.

**Agents:** `nova-scout` (haiku, locate files), `nova-reader` (sonnet, digest files), `nova-runner` (haiku, run tests and commands).

**Other-agent rule files:** `python -I scripts/build_adapters.py <folder>` writes AGENTS.md (Codex, OpenCode, Gemini, Antigravity), Cursor, Windsurf, Cline, Copilot, Kiro and Qoder rule files from `rules/core.md`.

**Always-on hooks (while the level is not off):**
- Session start: the rules for your level are added to context.
- Read: blocks a full re-read of a file that has not changed. Partial reads and edited files pass.
- Bash: blocks a bare `git diff` (use `--stat`, `--name-only` or `-U0`) and an identical read-only command within 30 seconds. The cache clears after any edit or shell command, so output is never stale.
- Before compaction: saves recent turns to `.claude/CONTEXT-SNAPSHOT.md`.
- Each prompt: warns once per session when the context passes 150,000 tokens (change with `NOVA_DEV_CONTEXT_WARN`), so you can `/compact` or start fresh before every turn gets expensive.

Level state lives in `~/.config/nova-dev/level` (override with the `NOVA_DEV_DIR` environment variable).
