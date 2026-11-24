"""Find the functions and classes that need an explanation: long enough to matter, and no
docstring or comment above them.

Usage: python -I scripts/annotate_targets.py <file or folder> [min_lines]   (default 8)
Python is read with ast (exact). Other languages use a simple pattern (approximate).
Output: file:line  name  (lines)  -- one line per target. Changes nothing.
"""
import ast
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
CODE_EXT = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cs", ".rb", ".php", ".kt", ".swift")
GENERIC = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:class)\s+(\w+)|func\s+(\w+)|fn\s+(\w+))")


def python_targets(text, min_lines):
    out = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    lines = text.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        span = (node.end_lineno or node.lineno) - node.lineno + 1
        if span < min_lines:
            continue
        documented = ast.get_docstring(node) is not None
        above = lines[node.lineno - 2].strip() if node.lineno >= 2 else ""
        if not documented and not above.startswith("#"):
            out.append((node.lineno, node.name, span))
    return sorted(out)


def generic_targets(text, min_lines):
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = GENERIC.match(line)
        if not m:
            continue
        name = next(g for g in m.groups() if g)
        indent = len(line) - len(line.lstrip())
        end = i + 1
        while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent):
            end += 1
        span = end - i
        above = lines[i - 1].strip() if i else ""
        if span >= min_lines and not above.startswith(("//", "#", "/*", "*", "\"\"\"")):
            out.append((i + 1, name, span))
    return out


def scan(root, min_lines=8):
    paths = [root] if os.path.isfile(root) else []
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            paths += [os.path.join(dirpath, f) for f in filenames if f.endswith(CODE_EXT)]
    results = []
    for path in sorted(paths):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        found = python_targets(text, min_lines) if path.endswith(".py") else generic_targets(text, min_lines)
        results += [(os.path.relpath(path, root if os.path.isdir(root) else os.path.dirname(root) or "."),
                     n, name, span) for n, name, span in found]
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    min_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    rows = scan(sys.argv[1], min_lines)
    print(f"{len(rows)} target(s) without an explanation")
    for rel, line, name, span in rows:
        print(f"{rel}:{line}  {name}  ({span} lines)")
    sys.exit(0)
