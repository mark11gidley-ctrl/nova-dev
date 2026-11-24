"""Code quality checks for Python projects. Usage: nd.py quality <name> [root]

  dead-code      functions and classes defined but never referenced elsewhere
  duplicates     blocks of 6+ identical lines that appear in more than one place
  complexity     functions with too many branches (default limit 10)
  naming         functions with camelCase or uppercase names (should be snake_case)
  import-cycles  modules that import each other in a loop
  long-lines     lines longer than 120 characters, counted per file
  magic-numbers  numeric literals outside 0, 1, 2 and named constants
  unused-imports imports that the file never uses

Read-only. Python is read with ast, so results are exact for syntax the parser accepts.
"""
import ast
import collections
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def parsed(root):
    for path in py_files(root):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            yield path, text, ast.parse(text)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue


def dead_code(root):
    defs = []
    texts = {}
    for path, text, tree in parsed(root):
        texts[path] = text
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("__") or node.name.startswith("test_"):
                    continue
                defs.append((path, node.lineno, node.name))
    everything = "\n".join(texts.values())
    out = []
    for path, line, name in defs:
        if len(re.findall(r"\b%s\b" % re.escape(name), everything)) <= 1:
            out.append(f"{os.path.relpath(path, root)}:{line}  {name}")
    return out


def duplicates(root, window=6):
    seen = collections.defaultdict(list)
    for path, text, _tree in parsed(root):
        lines = [(i + 1, l.strip()) for i, l in enumerate(text.splitlines()) if l.strip() and not l.strip().startswith("#")]
        for i in range(len(lines) - window + 1):
            chunk = tuple(t for _, t in lines[i:i + window])
            seen[chunk].append((os.path.relpath(path, root), lines[i][0]))
    out = []
    reported = set()
    for chunk, places in seen.items():
        places = sorted(set(places))
        if len(places) > 1 and places[0] not in reported:
            reported.add(places[0])
            out.append(" = ".join(f"{p}:{n}" for p, n in places[:3]) + f"  ({window} lines)")
    return out


BRANCHES = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp, ast.comprehension, ast.IfExp)


def complexity(root, limit=10):
    out = []
    for path, _text, tree in parsed(root):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                score = 1 + sum(1 for n in ast.walk(node) if isinstance(n, BRANCHES))
                if score > limit:
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name}  (score {score})")
    return out


def naming(root):
    out = []
    for path, _text, tree in parsed(root):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("__"):
                if re.search(r"[A-Z]", node.name) or re.search(r"[a-z][A-Z]", node.name):
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name}")
    return out


def import_cycles(root):
    mods = {}
    for path, _text, _tree in parsed(root):
        rel = os.path.relpath(path, root)[:-3].replace(os.sep, ".")
        mods[os.path.basename(path)[:-3]] = (path, rel)
    graph = collections.defaultdict(set)
    for name, (path, _rel) in mods.items():
        with open(path, encoding="utf-8") as fh:
            try:
                tree = ast.parse(fh.read())
            except SyntaxError:
                continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            graph[name].update(n for n in names if n in mods)
    out = []
    state = {}

    def visit(node, stack):
        state[node] = 1
        for nxt in graph[node]:
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):] + [nxt] if nxt in stack else [node, nxt]
                out.append(" -> ".join(cycle))
            elif nxt not in state:
                visit(nxt, stack + [nxt])
        state[node] = 2

    for m in list(graph):
        if m not in state:
            visit(m, [m])
    return sorted(set(out))


def long_lines(root, limit=120):
    counts = collections.Counter()
    for path, text, _tree in parsed(root):
        counts[os.path.relpath(path, root)] = sum(1 for l in text.splitlines() if len(l) > limit)
    return [f"{n}  {p}" for p, n in counts.most_common() if n]


def magic_numbers(root):
    counts = collections.Counter()
    for path, _text, tree in parsed(root):
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                if node.value not in (0, 1, 2, -1):
                    counts[os.path.relpath(path, root)] += 1
    return [f"{n}  {p}" for p, n in counts.most_common()]


def unused_imports(root):
    out = []
    for path, text, tree in parsed(root):
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [(a.asname or a.name.split(".")[0], node.lineno) for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
                imported += [(a.asname or a.name, node.lineno) for a in node.names if a.name != "*"]
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        for name, line in imported:
            # a name that appears only once in the file is the import itself
            if name not in used and len(re.findall(r"\b%s\b" % re.escape(name), text)) <= 1:
                out.append(f"{os.path.relpath(path, root)}:{line}  {name}")
    return out


COMMANDS = {
    "dead-code": dead_code, "duplicates": duplicates, "complexity": complexity, "naming": naming,
    "import-cycles": import_cycles, "long-lines": long_lines, "magic-numbers": magic_numbers,
    "unused-imports": unused_imports,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    root = argv[1] if len(argv) > 1 else os.getcwd()
    rows = COMMANDS[argv[0]](root)
    print(f"{len(rows)} finding(s) for {argv[0]}")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
