"""Bash guards.

bash  (PreToolUse Bash): blocks a bare `git diff` (full diff) and re-runs of an identical
      read-only command within 30 seconds.
clear (PostToolUse Edit|Write|MultiEdit|NotebookEdit|Bash): drops the query cache, so a
      read-only command never returns stale output after the code changed.
"""
import hashlib
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import cache_dir as _state_cache  # noqa: E402
from savings import record as _record_saving  # noqa: E402
import time

QUERY = re.compile(r"^\s*(git (log|status)\b|git diff --stat|git diff --name|cat |head |tail |grep |ls |find )")
DIFF = re.compile(r"\bgit\s+diff\b")
DIFF_OK = re.compile(r"--(stat|name-only|name-status|shortstat)|--unified=0|-U0")
DEDUP_SECONDS = 30


def cache_path(session_id, cache_dir=None, agent_id=None):
    sid = re.sub(r"[^\w-]", "_", f"{session_id or 'none'}-{agent_id}" if agent_id else str(session_id or "none"))
    return os.path.join(cache_dir or _state_cache(), f"bash-{sid}.json")


def decide_bash(data, cache_dir=None, now=None):
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    stripped = re.sub(r"\"[^\"]*\"|'[^']*'", "", cmd)
    if DIFF.search(stripped) and not DIFF_OK.search(cmd):
        return 2, ("nova-dev: a full git diff floods context. Run `git diff --stat` or "
                   "`git diff --name-only` first, then diff only the files you need "
                   "(or use -U0 for minimal context).")
    if not QUERY.match(cmd):
        return 0, None
    now = time.time() if now is None else now
    path = cache_path(data.get("session_id"), cache_dir, data.get("agent_id"))
    try:
        with open(path, encoding="utf-8") as fh:
            seen = json.load(fh)
    except (OSError, ValueError):
        seen = {}
    key = hashlib.sha256(re.sub(r"\s", "", cmd).encode()).hexdigest()
    last = seen.get(key)
    if last is not None and now - last < DEDUP_SECONDS:
        try:
            _record_saving("bash")
        except OSError:
            pass
        return 2, (f"nova-dev: this exact command ran {int(now - last)}s ago with no edits since. "
                   "Use that output already in context.")
    seen[key] = now
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(seen, fh)
    return 0, None


def decide_clear(data, cache_dir=None):
    path = cache_path(data.get("session_id"), cache_dir, data.get("agent_id"))
    try:
        os.remove(path)
    except OSError:
        pass
    return 0, None


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from state import get_level
    if get_level() not in ("lite", "full", "ultra"):
        sys.exit(0)
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    code, msg = decide_clear(data) if mode == "clear" else decide_bash(data)
    if msg:
        sys.stderr.write(msg + "\n")
    sys.exit(code)
