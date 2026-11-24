<p align="center">
  <img src="assets/icon.png" width="120" alt="Nova Dev icon">
</p>

<h1 align="center">Nova Dev</h1>

<p align="center">
  <b>Lazy-but-complete developer mode for Claude Code and Codex.</b><br>
  Writes the smallest change that fully works, checks every caller, adds one test for new logic,<br>
  and keeps token use in check.
</p>

---

## Why

- **Less code, same result.** Reuses what the codebase already has before writing anything new.
- **Nothing breaks quietly.** Every caller, test and fixture a change touches is checked.
- **Honest replies.** Every answer ends with what was skipped and what risk remains.
- **Measured, not guessed.** Token use and cache hits come from your own transcripts.
- **Private by default.** Nothing leaves your machine unless you set a webhook.

## Install

### What you need

| Requirement | Why | Check |
|-------------|-----|-------|
| Claude Code 2.1.290 or newer | Plugins and the band bar | `claude --version` |
| Python 3.9 or newer | Every hook and tool | `py -3 --version` (Windows) or `python3 --version` |
| Node.js (LTS) | Codex CLI and the Codex hook launcher | `node --version` |
| Git | Repository tools and the push workflow | `git --version` |
| ffmpeg (optional) | Video tools only | `ffmpeg -version` |

On Windows, the Python launcher `py -3` is preferred. A plain `python` can resolve to the Microsoft Store stub, which prints "Python was not found"; the hooks try `py -3` first, so this is handled.

### Option A: Claude Code, from GitHub (recommended)

In a terminal:

```
claude plugin marketplace add mark11gidley-ctrl/nova-dev
claude plugin install nova-dev@nova-dev
```

Or inside a Claude Code session, the same two commands with a leading slash: `/plugin marketplace add mark11gidley-ctrl/nova-dev`, then `/plugin install nova-dev@nova-dev`.

Start a new session afterwards. The first session tells you nova-dev is installed but inactive; choose a level (see below).

### Option B: Claude Code, from a local copy

Use this to try a checkout without installing it:

```
git clone https://github.com/mark11gidley-ctrl/nova-dev.git
claude --plugin-dir C:\path\to\nova-dev
```

`--plugin-dir` loads the plugin for that one run only.

### Option C: Codex

```
codex plugin marketplace add mark11gidley-ctrl/nova-dev
codex plugin add nova-dev@nova-dev
```

Then trust the hooks. Codex will not run a plugin's hooks until you approve them:

1. Run `codex`.
2. Type `/hooks`.
3. Trust nova-dev's two hooks (session start and prompt submit).
4. Start a new thread.

Codex runs the session-start and prompt hooks only; the read, Bash, compact and stop guards are Claude Code only. The rules also reach Codex through `AGENTS.md`.

### Option D: ChatGPT / Codex desktop app, without a terminal

Use this if you don't want to open a terminal. The desktop app's agent runs the same commands as Option C for you.

**Before you start**, install these with their normal installers (you can skip this if you already have them):

| Program | Get it from | Needed for |
|---------|-------------|------------|
| Python 3.9 or newer | python.org (tick "Add python.exe to PATH" on Windows) | every hook and tool |
| Node.js LTS | nodejs.org | the Codex plugin system |
| ffmpeg (optional) | `winget install Gyan.FFmpeg`, or gyan.dev | video tools only |

**Install the plugin with the app's window**

1. Open the Codex desktop app.
2. Open the plugins screen and choose **Add marketplace**.
3. Fill in the dialog:

   | Field | Enter |
   |-------|-------|
   | Source | `mark11gidley-ctrl/nova-dev` |
   | Git ref | `main` |
   | Sparse paths | leave empty |

4. Click **Add marketplace**. The app may ask you to sign in to GitHub first, because the repository is private.
5. In the marketplace, find **nova-dev** and click **Install**.
6. Close the app completely and open it again.
7. Approve nova-dev's two hooks (session start and prompt submit) on the plugin or hooks screen. If there is no such screen, use Option C to approve them.
8. In a new thread, type `nova dev status`. You should see the level and settings. Then choose a level, for example `nova dev full`.

**Or ask the app's agent to do it:** paste this message into a new thread:

> Install the nova-dev plugin for Codex. Add the marketplace `mark11gidley-ctrl/nova-dev`, then install `nova-dev@nova-dev` with the `codex plugin` commands. Show me each command and wait for my approval before running it.

Approve each command the app shows you.

**If the app won't run commands for you**, use Option C (the terminal steps), or ask someone who can run them for you.

*The dialog fields are from the Codex desktop app's "Add plugin marketplace" window. Not tested end to end yet; the app's menus may differ by version.*

### Install the prerequisites automatically

nova-dev can find and install what it needs. It never installs silently: it lists each missing item and the exact command, then asks you.

```
python -I scripts/nd.py setup          # list what is missing and ask item by item
python -I scripts/nd.py setup --yes    # install everything missing without asking
```

It uses winget on Windows, Homebrew on macOS, and apt on Linux. Open a new terminal afterwards so the new programs are on PATH.

### Check the install

```
python -I scripts/nd.py doctor
```

Run it from the plugin folder. It prints `N/N checks OK`. Any `FAIL` line says what is missing.

### Choose a level

Nothing is active until you choose one:

```
nova dev full
```

Or run the `nova-dev-init` skill, which asks you and writes `.claude/nova-dev.json` for the project.

### Update

```
claude plugin update nova-dev@nova-dev
codex plugin list
```

For Codex, remove and add again after an update: `codex plugin remove nova-dev@nova-dev`, then `codex plugin add nova-dev@nova-dev`. Re-trust the hooks if Codex asks.

### Uninstall

```
claude plugin uninstall nova-dev@nova-dev
claude plugin marketplace remove nova-dev
codex plugin remove nova-dev@nova-dev
```

Your settings and data stay in `~/.config/nova-dev/`. Delete that folder to remove them.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| The session says nova-dev is inactive | Choose a level: `nova dev full` |
| Hooks fail with "no Python" | Install Python 3 and make sure `py -3` or `python3` works in a new terminal |
| Codex shows "SessionStart Failed" | Trust the hooks in `/hooks`, then start a new thread |
| `doctor` reports a missing launcher | Add Python to PATH and open a new terminal |
| Video tools say ffmpeg is missing | `winget install Gyan.FFmpeg`, then open a new terminal |
| The status line stays empty | Add the statusline setting in Claude Code's settings (see `skills/nova-dev-band`) |

## Choose a level

nova-dev has **no default level**. Nothing is active until you choose one:

| Level | What it does |
|-------|--------------|
| `nova dev lite` | Builds what you asked. Names the smaller option and lets you pick. |
| `nova dev full` | The complete rules. Smallest change, every caller checked, one test for new logic. |
| `nova dev ultra` | Like full, and pushes back on any part the need does not justify. |
| `nova dev off` | Nothing active in this folder. |

Set it per project with `.claude/nova-dev.json`, or run `nova-dev-init`, which asks you.

## What you get

| Area | Features |
|------|----------|
| **Coding rules** | Smallest-change ladder, caller checks, test-for-logic rule, Skipped / Risk line |
| **Review** | `nova-dev-review`, `review-fast`, whole-repo `nova-dev-audit`, security and perf passes |
| **Tests** | `nova dev test` runs your tests and feeds the Stop gate; `testcheck` flags untested logic |
| **Context** | Read guard, Bash guard, context warning, auto-compact (opt-in), snapshot and handoff restore |
| **Measure** | `stats` (tokens and cache hit rate), per-project totals, `contexthist`, `hogs` |
| **Band** | Session ledger, HTML board, Markdown export, optional webhook |
| **Find and explain** | `find` past prompts, `callers`, `outline`, `annotate` |
| **Safety** | Secret redaction, secret scan, self-audit (`seccheck`), owner-only files |
| **Video** | 27 tools (probe, trim, concat, normalize, subtitles, edit lists, shot lists). Needs ffmpeg |
| **Agents** | `nova-scout` (locate), `nova-reader` (digest), `nova-runner` (tests), with model routing |

Run `python -I scripts/nd.py help` or see `skills/nova-dev-help` for the full list.

## Commands

In chat, type the level and status commands: `nova dev lite`, `nova dev full`, `nova dev ultra`, `nova dev off`, `nova dev status`.

Everything else runs from the CLI, `scripts/nd.py`:

```
python -I scripts/nd.py test              # run the project's tests, save the result for the Stop gate
python -I scripts/nd.py review            # compressed diff + secrets + test check
python -I scripts/nd.py find <words>      # search your past prompts
python -I scripts/nd.py stats 30 --by-project
python -I scripts/nd.py help              # every command
```

## Settings

Set them in `~/.config/nova-dev/config.json`, or as environment variables (which win).

| Key | Default | What it does |
|-----|---------|--------------|
| `level` | unset | The level you choose |
| `context_warn` | 150000 | Warn once when context passes this many tokens |
| `window` | 200000 | Context window size, for percentages |
| `autocompact` | false | Pause prompts at 55% of the window until you run `/compact` |
| `ledger` | true | Record each session in the band ledger |
| `webhook_url` | empty | https address that receives each session row (off by default) |
| `webhook_token` | empty | Sent as a bearer token. Environment variable only |
| `send_names` | false | Include task names (prompt text) in the webhook |
| `big_read` | 0 | Block whole-file reads longer than this many lines (0 = off) |

## Privacy and security

- Transcripts are read locally. Nothing is sent anywhere unless you set `webhook_url`.
- Secret-looking text is redacted before it reaches the ledger, the snapshot or a review.
- Files are written owner-only where the OS allows it.
- The plugin audits its own code: `nova dev seccheck`.

Details, including the known limits, are in [SECURITY.md](SECURITY.md).

## How it works

| Hook | When | What |
|------|------|------|
| Session start | Session begins | Adds the rules for your level |
| Prompt | You send a message | Level commands, context warning, optional auto-compact |
| Read | Before and after a file read | Blocks a repeat read of an unchanged file |
| Bash | Before a shell command | Blocks a bare `git diff` and an identical read-only command within 30 s |
| Pre-compact | Before `/compact` | Saves recent turns to `.claude/CONTEXT-SNAPSHOT.md` |
| Restore | After `/compact` or `/clear` | Puts the snapshot or a fresh handoff back |
| Stop | Session ends | Records the session and blocks stopping while tests fail |

Claude Code runs all hooks. Codex runs the session-start and prompt hooks.

## Development

Every self-check lives in `tests/`. Run them with `python -I tests/<file>.py`.

```
python -I scripts/doctor.py     # install check
python -I scripts/seccheck.py   # security self-audit
```

Layout: `hooks/` (runtime), `scripts/` (tools and CLI), `skills/` (one folder per skill), `agents/`, `rules/core.md` (source for the rule files built by `scripts/build_adapters.py`).

## License

MIT. See [LICENSE](LICENSE).
