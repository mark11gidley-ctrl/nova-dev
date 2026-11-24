#!/usr/bin/env python
"""Read dedup. "pre" blocks a full re-read of an unchanged file; "post" records a full read.

Fingerprint = mtime + size, so an edited file is always read again.
Partial reads (offset/limit) are never blocked and never recorded.
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import cache_dir as _state_cache  # noqa: E402


def cache_file(session_id, cache_dir=None, agent_id=None):
    # a subagent has its own context, so its reads are tracked separately from the main agent's
    sid = re.sub(r"[^\w-]", "_", f"{session_id or 'none'}-{agent_id}" if agent_id else str(session_id or "none"))
    return os.path.join(cache_dir or _state_cache(), f"read-{sid}.json")


def load_cache(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def fingerprint(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{st.st_mtime_ns}:{st.st_size}"


def is_full_read(tool_input):
    offset = tool_input.get("offset")
    limit = tool_input.get("limit")
    return offset in (None, 0) and limit is None


def decide(mode, data, cache_dir=None):
    """Return (exit_code, message). exit 2 blocks the Read and shows message to Claude."""
    tool_input = data.get("tool_input") or {}
    raw_path = tool_input.get("file_path")
    if not raw_path or not is_full_read(tool_input):
        return 0, None
    # one key per file, whatever the spelling: C:/x, C:\x and a relative path all name the same file
    file_path = os.path.normcase(os.path.abspath(raw_path))
    fp = fingerprint(file_path)
    if fp is None:
        return 0, None
    path = cache_file(data.get("session_id"), cache_dir, data.get("agent_id"))
    cache = load_cache(path)
    if mode == "pre":
        if cache.get(file_path) == fp:
            return 2, (f"nova-dev: {file_path} was already read this session and has not changed. "
                       "Use the earlier read instead of reading it again.")
        return 0, None
    cache[file_path] = fp
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)
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
    if os.environ.get("NOVA_DEV_HOOK_LOG"):  # opt-in debug: which fields Claude Code sends to this hook
        with open(os.environ["NOVA_DEV_HOOK_LOG"], "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"mode": mode, "keys": sorted(data.keys()),
                                 "session_id": data.get("session_id"), "agent_id": data.get("agent_id"),
                                 "file": (data.get("tool_input") or {}).get("file_path")}) + "\n")
    code, msg = decide(mode, data)
    if msg:
        sys.stderr.write(msg + "\n")
    sys.exit(code)
