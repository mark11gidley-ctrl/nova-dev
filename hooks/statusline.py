"""Statusline: context size, auto-compact distance, and last test result.
Point Claude Code's statusLine setting at this file (see skills/nova-dev-band). Reads only the
tail of the transcript, so it stays fast on every refresh."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context_watch import current_context_tokens, window  # noqa: E402
from tests_gate import status as test_status  # noqa: E402


def line(data):
    cwd = data.get("cwd") or os.getcwd()
    tokens = current_context_tokens(data.get("transcript_path"))
    parts = []
    if tokens is not None:
        pct = int(tokens * 100 / window())
        parts.append(f"ctx {pct}% ({tokens:,})")
    tests = test_status(cwd)
    parts.append(f"tests {tests}" if tests else "tests -")
    return "nova-dev | " + " | ".join(parts)


def band_line(cwd):
    """One line for the band UI: level and last test result. No transcript needed."""
    from state import get_level
    tests = test_status(cwd)
    label = {"pass": "tests pass", "fail": "tests FAIL", None: "tests -"}[tests]
    return f"nova-dev {get_level(cwd)} | {label}"


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--band":
        print(band_line(sys.argv[2]))
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    try:
        print(line(data))
    except OSError:
        print("nova-dev")
    sys.exit(0)
