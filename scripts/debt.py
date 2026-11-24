"""List deferred shortcuts: a code comment saying the shortcut's limit and when to upgrade.

Usage: python -I scripts/debt.py [root] [word]   (root defaults to the current folder, word to "shortcut")
"""
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
MAX_FILE_BYTES = 2_000_000


def comment_pattern(word="shortcut"):
    return re.compile(r"(?:#|//|/\*|--|<!--)\s*(" + re.escape(word) + r":|ponytail:)\s*(.+?)\s*(?:\*/|-->)?\s*$")


def scan(root, word="shortcut"):
    pattern = comment_pattern(word)
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.startswith("test_") and name.endswith(".py"):
                continue  # test fixtures contain example markers, not real deferrals
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, 1):
                m = pattern.search(line)
                if m:
                    hits.append((os.path.relpath(path, root), number, m.group(2)))
    return hits


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    word = sys.argv[2] if len(sys.argv) > 2 else "shortcut"
    hits = scan(root, word)
    print(f"{len(hits)} deferred shortcut(s) in {root}")
    for rel, number, text in hits:
        print(f"{rel}:{number}  {text}")
    sys.exit(0)
