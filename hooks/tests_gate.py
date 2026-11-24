"""Test status from the last test run, read from .claude/last_test_output.txt in the git root.
Used by the Stop gate (blocks stopping while tests fail) and the statusline."""
import os
import re
import time

FAIL = re.compile(r"Tests .* failed|Test Files .* failed")
FRESH_SECONDS = 300


def git_root(cwd):
    """Walk up from cwd to the folder holding .git. No subprocess, so the status line stays fast."""
    path = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def log_path(cwd):
    root = git_root(cwd) if cwd else None
    return os.path.join(root, ".claude", "last_test_output.txt") if root else None


def counts(cwd):
    """(passed, failed) from the last test log, or None when there is no log or no count in it."""
    path = log_path(cwd)
    if not path:
        return None
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    passed = re.findall(r"(\d+) passed", text)
    failed = re.findall(r"(\d+) failed", text)
    if not passed and not failed:
        return None
    return (int(passed[-1]) if passed else 0, int(failed[-1]) if failed else 0)


def status(cwd, now=None, fresh=FRESH_SECONDS):
    """'fail', 'pass', or None when there is no recent test log."""
    path = log_path(cwd)
    if not path:
        return None
    try:
        age = (time.time() if now is None else now) - os.path.getmtime(path)
    except OSError:
        return None
    if age > fresh:
        return None
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    # the explicit marker from scripts/runtests.py wins; the regex is for logs from other runners
    last = text.rfind("nova-dev: RESULT ")
    if last >= 0:
        return "fail" if text[last:].startswith("nova-dev: RESULT fail") else "pass"
    return "fail" if FAIL.search(text) else "pass"
