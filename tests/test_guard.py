"""Self-check: python -I tests/test_guard.py  (exits 0 on success)."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
from guard import decide_bash, decide_clear  # noqa: E402

work = tempfile.mkdtemp(prefix="tl-guard-")
c = os.path.join(work, "c")
os.makedirs(c)
s = {"session_id": "t1"}

def bash(cmd, now=None):
    return decide_bash({**s, "tool_input": {"command": cmd}}, c, now)[0]

# full git diff blocked; summary forms allowed
assert bash("git diff") == 2
assert bash("git diff --stat") == 0
assert bash("git diff -U0 src/a.py") == 0
# identical read-only command deduped within 30s, allowed after
assert bash("git status", now=1000) == 0
assert bash("git status", now=1010) == 2
assert bash("git status", now=1040) == 0
# clearing the cache (after an edit) allows it immediately again
decide_clear(s, c)
assert bash("git status", now=1041) == 0
# non-query commands are never deduped
assert bash("npm test", now=2000) == 0
assert bash("npm test", now=2001) == 0

shutil.rmtree(work, ignore_errors=True)
print("guard: all checks passed")
