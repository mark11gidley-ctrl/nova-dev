# Security

## What nova-dev reads and writes

| Data | Where | Leaves the machine? |
|------|-------|---------------------|
| Session transcripts (`~/.claude/projects/...`) | Read by stats, band, find, context tools | No |
| Band ledger (one row per session: tokens, project, redacted first prompt) | `~/.config/nova-dev/band/*.csv` | No, unless the webhook is set |
| Webhook (off by default) | Sends one row per session as JSON | Yes, to the https URL you set |
| Pre-compact snapshot (recent turns, redacted) | `<project>/.claude/CONTEXT-SNAPSHOT.md`, owner-only where the OS allows | No |
| Hook caches (read and command dedup) | `~/.config/nova-dev/cache/` | No |
| Level and settings | `~/.config/nova-dev/` | No |

## Controls

- **Webhook:** https only. The token is read from the `NOVA_DEV_WEBHOOK_TOKEN` environment variable only, never from a file. Task names are not sent unless `send_names` is on, and it is off by default.
- **Redaction:** secret-looking text (AWS keys, GitHub and Slack tokens, private key blocks, assigned passwords and keys) is replaced with `[hidden: <kind>]` before it reaches the ledger, the snapshot, the review bundle, or the scanner output. Values are never printed.
- **Spreadsheet export:** cells that start with `= + - @` are prefixed so spreadsheets do not run them as formulas.
- **Caches:** kept in the private state folder, not the shared temp folder, so another local user cannot plant a file there.
- **Self-audit:** `scripts/seccheck.py` scans the plugin's own Python for shell=True, os.system, eval/exec, unsafe pickle and yaml loads, disabled TLS checks, plain http URLs and hardcoded credentials. Its allow list is short and each entry has a reason.

## Known limits

- Redaction is pattern-based. It catches common formats, not every secret. Treat the ledger and snapshot as sensitive files.
- The plugin runs hooks with your user rights, as any Claude Code plugin does. Install only code you have read.
- Snapshot and ledger files are plain text on your disk. Anyone with access to your user account can read them.
- Windows does not enforce the owner-only file mode, so the snapshot's privacy there depends on your folder permissions.

## Reporting

Report a security problem to the project owner directly, not in a public issue. Include the version, the steps, and the impact. Rotate any credential that may have been exposed.
