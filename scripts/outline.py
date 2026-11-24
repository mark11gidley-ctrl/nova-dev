"""Outline a file: definitions and headings with line numbers, so Claude reads only the ranges it needs.

Usage: python -I scripts/outline.py <file> [max_lines]   (default cap 200 lines)
"""
import re
import sys

DEF = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:def |class |function |fn |func |impl |struct |enum |interface |type |trait )"
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?(?:\(|function)"
    r"|^#{1,6}\s"
)


def outline(text, cap=200):
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        if DEF.search(line):
            out.append(f"{number}: {line.rstrip()[:140]}")
            if len(out) >= cap:
                out.append(f"... capped at {cap} entries")
                break
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    with open(sys.argv[1], encoding="utf-8", errors="ignore") as fh:
        print("\n".join(outline(fh.read(), cap)) or "no definitions or headings found")
    sys.exit(0)
