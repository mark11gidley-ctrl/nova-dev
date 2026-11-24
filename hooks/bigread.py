"""PreToolUse Read (opt-in): block a whole-file read of a long file and point to outline + ranged reads.

Off unless NOVA_DEV_BIG_READ is set to a line count, e.g. 800. Partial reads always pass."""
import json
import os
import sys


def decide(data, limit):
    if limit <= 0:
        return 0, None
    inp = data.get("tool_input") or {}
    path = inp.get("file_path")
    if not path or inp.get("offset") or inp.get("limit"):
        return 0, None
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = sum(1 for _ in fh)
    except OSError:
        return 0, None
    if lines <= limit:
        return 0, None
    return 2, (f"nova-dev: {path} has {lines} lines. Run scripts/outline.py on it to find the part you need, "
               "then Read with offset and limit.")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from settings import get as setting
    limit = setting("big_read")
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    code, msg = decide(data, limit)
    if msg:
        sys.stderr.write(msg + "\n")
    sys.exit(code)
