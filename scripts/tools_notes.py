"""Code notes checks. Usage: nd.py notes <name> [root]

  todo          TODO, FIXME, HACK and XXX markers with file and line
  docparams     Python docstrings that do not mention every parameter
  stale-notes   comments that name a function, class or file no longer in the repo
  header-check  source files with no comment or docstring at the top
  note-density  comment lines as a share of code, per file, highest first

Read-only.
"""
import ast
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
CODE_EXT = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h", ".cs", ".rb", ".php")
MARK = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--)")


def files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(CODE_EXT):
                yield os.path.join(dirpath, f)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def todo(root):
    out = []
    for path in files(root):
        text = read(path) or ""
        for i, line in enumerate(text.splitlines(), 1):
            if MARK.search(line):
                out.append(f"{os.path.relpath(path, root)}:{i}  {line.strip()[:120]}")
    return out


def docparams(root):
    out = []
    for path in files(root):
        if not path.endswith(".py"):
            continue
        text = read(path) or ""
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if not doc:
                    continue
                params = [a.arg for a in node.args.args + node.args.kwonlyargs if a.arg not in ("self", "cls")]
                missing = [p for p in params if not re.search(r"\b%s\b" % re.escape(p), doc)]
                if missing:
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name}: not in docstring: {', '.join(missing)}")
    return out


def stale_notes(root):
    all_text = {}
    for path in files(root):
        all_text[path] = read(path) or ""
    corpus = "\n".join(all_text.values())
    out = []
    for path, text in all_text.items():
        for i, line in enumerate(text.splitlines(), 1):
            if not COMMENT.match(line):
                continue
            for name in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)\(?\)?`", line):
                if len(re.findall(r"\b%s\b" % re.escape(name), corpus)) <= 1:
                    out.append(f"{os.path.relpath(path, root)}:{i}  `{name}` is not defined anywhere")
    return out


def header_check(root):
    out = []
    for path in files(root):
        text = read(path)
        if text is None:
            continue
        first = next((l for l in text.splitlines() if l.strip() and not l.startswith("#!")), "")
        if not (COMMENT.match(first) or first.lstrip().startswith(('"""', "'''"))):
            out.append(os.path.relpath(path, root))
    return out


def note_density(root):
    rows = []
    for path in files(root):
        text = read(path)
        if not text:
            continue
        lines = [l for l in text.splitlines() if l.strip()]
        comments = sum(1 for l in lines if COMMENT.match(l))
        code = len(lines) - comments
        if code:
            rows.append((comments / len(lines) * 100, os.path.relpath(path, root), comments, code))
    rows.sort(reverse=True)
    return [f"{pct:5.1f}%  {p}  ({c} comment / {k} code lines)" for pct, p, c, k in rows]


COMMANDS = {"todo": todo, "docparams": docparams, "stale-notes": stale_notes,
            "header-check": header_check, "note-density": note_density}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    root = argv[1] if len(argv) > 1 else os.getcwd()
    rows = COMMANDS[argv[0]](root)
    print(f"{len(rows)} result(s) for notes {argv[0]}")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
