"""UserPromptSubmit: switch the level from a typed command, and warn once when the
session's context is large. Never blocks a prompt."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import set_level  # noqa: E402
from context_watch import autocompact_block, current_context_tokens, warn_once  # noqa: E402

SET = re.compile(r"^\s*(?:/nova-dev|nova dev)\s+(lite|full|ultra|off)\s*$", re.I)
STOP = re.compile(r"^\s*(?:stop nova dev|normal mode)\s*$", re.I)
STATUS = re.compile(r"^\s*(?:/nova-dev|nova dev)\s+(status|config)\s*$", re.I)


EXEMPT = re.compile(r"^\s*(/compact|/clear|/nova-dev|nova dev|stop nova dev|normal mode)\b", re.I)


def is_exempt(prompt):
    """Prompts that must never be blocked: the commands that clear the blockage, and nova dev's own."""
    return bool(EXEMPT.match(prompt or ""))


def decide(prompt):
    if STATUS.match(prompt):
        from settings import summary
        from state import get_level
        return ("Nova dev status (show this to the user as-is):\n"
                f"level (this folder): {get_level(os.getcwd())}\n{summary()}")
    m = SET.match(prompt)
    if m:
        level = m.group(1).lower()
        set_level(level)
        return f"Nova dev level is now {level}."
    if STOP.match(prompt):
        set_level("off")
        return "Nova dev is off. Normal mode."
    return None


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    tokens = current_context_tokens(data.get("transcript_path"))
    prompt = data.get("prompt", "") or ""
    # never block the commands that fix the blockage: /compact, /clear, and nova dev commands
    block = None if is_exempt(prompt) else autocompact_block(data.get("session_id"), tokens)
    if block:
        sys.stderr.write(block + "\n")
        sys.exit(2)
    notes = [n for n in (
        decide(data.get("prompt", "")),
        warn_once(data.get("session_id"), tokens),
    ) if n]
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": "\n".join(notes)}}))
    sys.exit(0)
