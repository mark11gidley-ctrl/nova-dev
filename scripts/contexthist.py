"""Context size per turn for one session, with the turns where it jumped.

Usage: python -I scripts/contexthist.py <transcript.jsonl>
A turn's context is the prompt size it was sent with: fresh input plus cached input.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
from usage import context_size, read_usage  # noqa: E402


def history(path):
    usage, _ = read_usage(path)
    return [context_size(tup) for _ts, tup in usage.values()]


def render(sizes):
    if not sizes:
        return "no assistant turns with usage found"
    lines = [f"{len(sizes)} turn(s); peak {max(sizes):,}; last {sizes[-1]:,}"]
    prev = 0
    for i, s in enumerate(sizes, 1):
        jump = " <- jump" if prev and s - prev > 5000 and s > prev * 1.2 else ""
        lines.append(f"  turn {i:>4}: {s:>10,}{jump}")
        prev = s
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    print(render(history(sys.argv[1])))
    sys.exit(0)
