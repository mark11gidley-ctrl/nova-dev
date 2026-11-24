"""Find every place a symbol is used, before you change it.

Usage: python -I scripts/callers.py <symbol> [root]   (root defaults to the current folder)
"""
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".cs", ".rb",
              ".php", ".swift", ".c", ".h", ".cc", ".cpp", ".md", ".json", ".yaml", ".yml", ".toml"}


def find_callers(symbol, root):
    pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() not in SOURCE_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, 1):
                if pattern.search(line):
                    hits.append((os.path.relpath(path, root), number, line.strip()[:160]))
    return hits


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    symbol = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    hits = find_callers(symbol, root)
    print(f"{len(hits)} use(s) of {symbol}")
    for rel, number, text in hits:
        print(f"{rel}:{number}  {text}")
    sys.exit(0)
