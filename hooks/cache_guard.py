"""PostToolUse Edit/Write: warn when an always-on file changes mid-session.

The prompt cache stores everything sent before a change. Editing AGENTS.md, CLAUDE.md or the rules file
makes the next turn rebuild that cache, which costs more than a normal turn. The warning says so once per
file per session, so the user can finish the task first or start a new session."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import state_dir  # noqa: E402

ALWAYS_ON = re.compile(r"(^|[\\/])(AGENTS\.md|CLAUDE\.md|rules[\\/]core\.md)$", re.I)


def advice(data):
    """Return the warning text for this tool call, or None. Each file warns once per session."""
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not ALWAYS_ON.search(path):
        return None
    flag_dir = os.path.join(state_dir(), "cachewarn")
    key = "".join(c if c.isalnum() else "_" for c in f"{data.get('session_id', 'none')}-{os.path.basename(path)}")
    flag = os.path.join(flag_dir, key)
    if os.path.exists(flag):
        return None
    os.makedirs(flag_dir, exist_ok=True)
    open(flag, "w").close()
    return (f"nova-dev: {os.path.basename(path)} is always-on context. Changing it mid-session rebuilds the "
            "prompt cache on the next turn, which costs extra tokens. Finish this task first, or start a new "
            "session after the change.")


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    msg = advice(data)
    if msg:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
    sys.exit(0)
