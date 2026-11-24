"""Context and token helpers. Usage: nd.py ctx <name> [args]

  always-on-size      words in the rules that load every session (rules/core.md and the session prompt)
  forecast <transcript>  turns left before the window is full, from the measured growth per turn
  cache-breaks <transcript>  turns where the cached prompt dropped (the cache was rebuilt, which costs more)
  big-files [root] [n]   the largest files: the most context they cost if read whole

Read-only. Token numbers come from transcripts, not estimates.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
from usage import context_size, read_usage  # noqa: E402

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
ALWAYS_ON = ["AGENTS.md", os.path.join("rules", "core.md"), "CLAUDE.md"]


def always_on_size(root):
    rows = []
    total = 0
    for rel in ALWAYS_ON:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            words = len(open(path, encoding="utf-8", errors="ignore").read().split())
            total += words
            rows.append(f"{words:6d} words  {rel}")
    rows.append(f"{total:6d} words  total always-on text (loads every session if these files are in the project)")
    if total > 600:
        rows.append("suggestion: trim always-on rules, or move detail into an on-demand skill")
    return rows


def forecast(path, window=None):
    window = window or int(os.environ.get("NOVA_DEV_WINDOW", 200_000))
    usage, _ = read_usage(path)
    sizes = [context_size(t) for _ts, t in usage.values()]
    if len(sizes) < 2:
        return ["need at least two turns to forecast"]
    growth = (sizes[-1] - sizes[0]) / (len(sizes) - 1)
    if growth <= 0:
        return [f"context is not growing (last {sizes[-1]:,} tokens)"]
    left = max(0, window - sizes[-1])
    return [f"last context {sizes[-1]:,} of {window:,} tokens",
            f"average growth {growth:,.0f} tokens per turn",
            f"about {int(left / growth)} turn(s) before the window is full"]


def cache_breaks(path):
    usage, _ = read_usage(path)
    rows = []
    prev = None
    for i, (_ts, (inp, out, cache_read, cache_create)) in enumerate(usage.values(), 1):
        if prev is not None and prev > 0 and cache_read < prev * 0.5:
            rows.append(f"turn {i}: cached prompt fell from {prev:,} to {cache_read:,} (cache rebuilt)")
        prev = cache_read
    return rows or ["no cache breaks found"]


def big_files(root, top=10):
    sizes = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            try:
                sizes.append((os.path.getsize(p), os.path.relpath(p, root)))
            except OSError:
                continue
    sizes.sort(reverse=True)
    return [f"{size / 1024:9.1f} KB  {rel}" for size, rel in sizes[:top]]


def main(argv):
    names = {"always-on-size", "forecast", "cache-breaks", "big-files"}
    if not argv or argv[0] not in names:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "always-on-size":
        rows = always_on_size(rest[0] if rest else os.getcwd())
    elif cmd == "forecast":
        rows = forecast(rest[0])
    elif cmd == "cache-breaks":
        rows = cache_breaks(rest[0])
    else:
        rows = big_files(rest[0] if rest else os.getcwd(), int(rest[1]) if len(rest) > 1 else 10)
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
