"""Scan added lines of a diff for secrets. Prints file, line and kind only, never the value.

Usage: git diff --cached | python -I scripts/secret_scan.py
Exit 0 when clean, 1 when a secret pattern was found.
(Named secret_scan, not secrets, so it never shadows Python's standard secrets module.)
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
from redact import MAX_LINE, line_kind  # noqa: E402

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def redact(diff_lines):
    """Replace any added line that holds a secret with a marker, so the diff can be shown safely."""
    out = []
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            kind = line_kind(line[1:])
            if kind:
                out.append(f"+[line hidden: {kind}]")
                continue
        out.append(line)
    return out


def scan(diff_text):
    findings = []
    path = "?"
    new_line = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            if path.startswith("b/"):
                path = path[2:]
            continue
        m = HUNK.match(line)
        if m:
            new_line = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            kind = line_kind(line[1:MAX_LINE + 1])
            if kind:
                findings.append((path, new_line, kind))
            new_line += 1
        elif line.startswith(" "):
            new_line += 1
    return findings


if __name__ == "__main__":
    found = scan(sys.stdin.read())
    if not found:
        print("no secrets found in added lines")
        sys.exit(0)
    for path, number, kind in found:
        print(f"{path}:{number}  {kind} (value hidden)")
    sys.exit(1)
