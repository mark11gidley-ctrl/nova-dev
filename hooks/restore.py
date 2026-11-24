"""SessionStart: put context back after a reset.

- source "compact": the pre-compact snapshot (.claude/CONTEXT-SNAPSHOT.md), written by the PreCompact hook.
- source "clear": a handoff note (.claude/HANDOFF.md) written by nova-dev-handoff, if it is under 24 hours old.
Claude Code passes `source` (startup, resume, clear, compact). Startup and resume pay nothing."""
import json
import os
import sys
import time

CAP = 6000
HANDOFF_CAP = 4000
HANDOFF_MAX_AGE = 24 * 3600


def _read(path, cap, label, tail=True):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return ""
    if len(text) > cap:
        text = ("...(earlier truncated)...\n" + text[-cap:]) if tail else (text[:cap] + "\n...(truncated)")
    return f"<nova-dev-{label}>\n{text}\n</nova-dev-{label}>\n"


def restore_text(data, now=None):
    cwd = data.get("cwd") or os.getcwd()
    source = data.get("source")
    if source == "compact":
        return _read(os.path.join(cwd, ".claude", "CONTEXT-SNAPSHOT.md"), CAP, "snapshot")
    if source == "clear":
        path = os.path.join(cwd, ".claude", "HANDOFF.md")
        try:
            fresh = (time.time() if now is None else now) - os.path.getmtime(path) < HANDOFF_MAX_AGE
        except OSError:
            return ""
        return _read(path, HANDOFF_CAP, "handoff", tail=False) if fresh else ""
    return ""


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    sys.stdout.write(restore_text(data))
    sys.exit(0)
