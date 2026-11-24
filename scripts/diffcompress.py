"""Compress a git diff for review: keep headers and changed lines, cap changed lines per file.

Usage: git diff HEAD | python -I scripts/diffcompress.py [cap_per_file]   (default 80)
"""
import sys


def compress(text, cap=80):
    out = []
    dropped = 0
    changed = 0

    def close_file():
        nonlocal dropped, changed
        if dropped:
            out.append(f"... {dropped} more changed lines in this file")
        dropped = 0
        changed = 0

    for line in text.splitlines():
        if line.startswith("diff --git"):
            close_file()
            out.append(line)
        elif line.startswith(("+++", "---", "@@", "index ")):
            out.append(line)
        elif line.startswith(("+", "-")):
            changed += 1
            if changed <= cap:
                out.append(line)
            else:
                dropped += 1
    close_file()
    return out


if __name__ == "__main__":
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    print("\n".join(compress(sys.stdin.read(), cap)))
    sys.exit(0)
