"""Testing helpers. Usage: nd.py tests <name> [args]

  gen-test <file> <function>  print a test skeleton for a Python function (does not write files)
  flaky [runs]                run the project's tests several times; report if the result changes
  coverage-gap [root]         functions whose name appears in no test file
  test-names [root]           test functions in tests/ that pytest would not collect (no test_ prefix)
  assert-free [root]          test functions that contain no assertion
  slow-tests [root]           each test file's wall time, slowest first

Runs test commands only when you ask (flaky, slow-tests). Otherwise read-only.
"""
import ast
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def py_files(root, only_tests=None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            is_test = f.startswith("test_") or f.endswith("_test.py") or "tests" in dirpath.split(os.sep)
            if only_tests is None or only_tests == is_test:
                yield os.path.join(dirpath, f)


def gen_test(path, func):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
            args = ", ".join(f"{p}=None" for p in params)
            mod = os.path.splitext(os.path.basename(path))[0]
            return [
                f"from {mod} import {func}",
                "",
                f"def test_{func}_normal_case():",
                f"    # TODO: a typical input and the expected result",
                f"    assert {func}({args}) is not None",
                "",
                f"def test_{func}_edge_case():",
                f"    # TODO: the empty, zero or boundary input that would break users",
                "    pass",
            ]
    return [f"no function named {func} in {path}"]


def flaky(root, runs=3):
    sys.path.insert(0, HERE)
    import runtests
    cmd = runtests.detect(root)
    if not cmd:
        return ["no test command found"]
    results = []
    for _ in range(runs):
        code, _text = runtests.run(cmd, root)
        results.append(code)
    if len(set(results)) == 1:
        return [f"stable: {runs} runs, all exit {results[0]}"]
    return [f"FLAKY: exit codes {results} over {runs} runs"]


def coverage_gap(root):
    tests_text = ""
    for path in py_files(root, only_tests=True):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            tests_text += fh.read()
    out = []
    for path in py_files(root, only_tests=False):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            try:
                tree = ast.parse(fh.read())
            except SyntaxError:
                continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if not re.search(r"\b%s\b" % re.escape(node.name), tests_text):
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name}")
    return out


def test_names(root):
    out = []
    for path in py_files(root, only_tests=True):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            try:
                tree = ast.parse(fh.read())
            except SyntaxError:
                continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith(("test_", "_")):
                if node.name not in ("main", "setUp", "tearDown"):
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name} (not collected as a test)")
    return out


def assert_free(root):
    out = []
    for path in py_files(root, only_tests=True):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            try:
                tree = ast.parse(fh.read())
            except SyntaxError:
                continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                has = any(isinstance(n, ast.Assert) or (isinstance(n, ast.Call) and getattr(n.func, "attr", "").startswith("assert"))
                          for n in ast.walk(node))
                if not has:
                    out.append(f"{os.path.relpath(path, root)}:{node.lineno}  {node.name}")
    return out


def slow_tests(root):
    rows = []
    for path in py_files(root, only_tests=True):
        if not os.path.basename(path).startswith("test_"):
            continue
        start = time.time()
        subprocess.run([sys.executable, "-I", path], capture_output=True, timeout=600)
        rows.append((time.time() - start, os.path.relpath(path, root)))
    rows.sort(reverse=True)
    return [f"{secs:6.2f}s  {p}" for secs, p in rows]


def main(argv):
    names = {"gen-test", "flaky", "coverage-gap", "test-names", "assert-free", "slow-tests"}
    if not argv or argv[0] not in names:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    root = os.getcwd()
    if cmd == "gen-test":
        rows = gen_test(rest[0], rest[1])
    elif cmd == "flaky":
        rows = flaky(root, int(rest[0]) if rest else 3)
    elif cmd == "coverage-gap":
        rows = coverage_gap(rest[0] if rest else root)
    elif cmd == "test-names":
        rows = test_names(rest[0] if rest else root)
    elif cmd == "assert-free":
        rows = assert_free(rest[0] if rest else root)
    else:
        rows = slow_tests(rest[0] if rest else root)
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
