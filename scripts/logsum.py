"""Shrink a long log to what matters: failing lines with two lines of context, plus the tail.

Usage: python -I scripts/logsum.py <file> [max_lines]   (default 60)
"""
import re
import sys

FAIL = re.compile(r"\b(fail(ed|ure)?|error|exception|traceback|assert|panic|fatal|FAIL)\b", re.I)


def summarize(text, cap=60, context=2, tail=10):
    lines = text.splitlines()
    keep = set()
    for i, line in enumerate(lines):
        if FAIL.search(line):
            keep.update(range(max(0, i - context), min(len(lines), i + context + 1)))
    keep.update(range(max(0, len(lines) - tail), len(lines)))
    chosen = [i for i in sorted(keep)]
    out = []
    prev = None
    for i in chosen:
        if prev is not None and i != prev + 1:
            out.append("...")
        out.append(f"{i + 1}: {lines[i][:200]}")
        prev = i
    if len(out) > cap:
        out = out[:cap] + [f"... {len(out) - cap} more lines omitted"]
    header = f"{len(lines)} lines in log; {sum(1 for l in lines if FAIL.search(l))} failing-looking lines"
    return [header] + out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    with open(sys.argv[1], encoding="utf-8", errors="ignore") as fh:
        print("\n".join(summarize(fh.read(), cap)))
    sys.exit(0)
