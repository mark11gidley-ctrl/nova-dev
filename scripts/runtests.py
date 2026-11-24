"""Run the project's tests and save the output where the Stop gate reads it.

Usage: python -I scripts/runtests.py [command ...]
  With no command: detects npm test (package.json), or pytest / unittest (Python projects).
Writes <repo root>/.claude/last_test_output.txt ending with a line 'nova-dev: RESULT pass|fail'.
Exit code = the test command's exit code (2 when no command can be found).
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
from tests_gate import git_root  # noqa: E402


def detect(root):
    pkg = os.path.join(root, "package.json")
    if os.path.isfile(pkg):
        try:
            with open(pkg, encoding="utf-8") as fh:
                scripts = json.load(fh).get("scripts", {})
        except (OSError, ValueError):
            scripts = {}
        if scripts.get("test"):
            return ["npm", "test"]
    python_project = any(os.path.isfile(os.path.join(root, f))
                         for f in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"))
    if python_project or os.path.isdir(os.path.join(root, "tests")):
        if importlib.util.find_spec("pytest") is not None:
            return [sys.executable, "-m", "pytest"]
        if os.path.isdir(os.path.join(root, "tests")):  # tests/ without __init__.py needs -s to be found
            return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"]
        return [sys.executable, "-m", "unittest", "discover"]
    return None


def run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)
    result = "pass" if proc.returncode == 0 else "fail"
    text = (proc.stdout or "") + (proc.stderr or "") + f"\nnova-dev: RESULT {result}\n"
    return proc.returncode, text


def log_path(root):
    return os.path.join(root, ".claude", "last_test_output.txt")


def cached_result(root):
    """The last saved result, if nothing has changed since it was written. Returns (exit_code, text) or None.

    Reused only inside a git repository, and only when no file in the working tree is newer than the log and
    no commit is newer than the log. Anything else means the tests run again."""
    path = log_path(root)
    if not os.path.isfile(path):
        return None
    log_time = os.path.getmtime(path)
    status = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True)
    head = subprocess.run(["git", "-C", root, "log", "-1", "--format=%ct"], capture_output=True, text=True)
    if status.returncode != 0 or head.returncode != 0 or not head.stdout.strip():
        return None
    if int(head.stdout.strip()) > log_time:
        return None
    for line in status.stdout.splitlines():
        rel = line[3:].split(" -> ")[-1].strip('"')
        full = os.path.join(root, rel)
        if not os.path.exists(full) or os.path.getmtime(full) > log_time:
            return None
    with open(path, encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    last = text.rfind("nova-dev: RESULT ")
    if last < 0:
        return None
    return (0 if text[last:].startswith("nova-dev: RESULT pass") else 1), text


if __name__ == "__main__":
    force = "--force" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--force"]
    cwd = os.getcwd()
    root = git_root(cwd) or cwd
    if not force and not args:
        cached = cached_result(root)
        if cached:
            code, text = cached
            print("cached: nothing changed since the last test run; showing that result (use --force to run again)")
            print("\n".join(text.splitlines()[-6:]))
            sys.exit(code)
    cmd = args or detect(root)
    if not cmd:
        print("nova-dev: no test command found. Pass one, e.g. runtests.py python -m pytest")
        sys.exit(2)
    code, text = run(cmd, root)
    os.makedirs(os.path.dirname(log_path(root)), exist_ok=True)
    with open(log_path(root), "w", encoding="utf-8") as fh:
        fh.write(text)
    tail = "\n".join(text.splitlines()[-12:])
    print(tail)
    print(f"(full output: {log_path(root)})")
    sys.exit(code)
