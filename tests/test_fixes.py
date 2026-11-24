"""Self-check for the audit fixes: python -I tests/test_fixes.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
work = tempfile.mkdtemp(prefix="nd-fix-")
os.environ["NOVA_DEV_DIR"] = work
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import init  # noqa: E402
import ledger  # noqa: E402
import prompt_submit  # noqa: E402
import read_dedup  # noqa: E402
import stop  # noqa: E402
import tests_gate  # noqa: E402
from usage import read_usage  # noqa: E402

# 1. init: a .gitignore without a final line break keeps every entry on its own line
repo = os.path.join(work, "repo")
os.makedirs(os.path.join(repo, ".git"))
with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as fh:
    fh.write("node_modules")
init.init(repo)
lines = open(os.path.join(repo, ".gitignore"), encoding="utf-8").read().splitlines()
assert "node_modules" in lines and ".claude/CONTEXT-SNAPSHOT.md" in lines, lines

# 2. /compact, /clear and nova dev commands are never blocked by auto-compact
for prompt in ("/compact", "  /clear", "/nova-dev status", "nova dev lite", "normal mode"):
    assert prompt_submit.is_exempt(prompt), prompt
assert not prompt_submit.is_exempt("please refactor the parser")

# 3. the test gate still runs when the ledger step fails
repo2 = os.path.join(work, "repo2")
os.makedirs(os.path.join(repo2, ".git"))
os.makedirs(os.path.join(repo2, ".claude"))
with open(os.path.join(repo2, ".claude", "last_test_output.txt"), "w", encoding="utf-8") as fh:
    fh.write(" Tests  1 failed | 4 passed (5)\n")
transcript = os.path.join(work, "t.jsonl")
with open(transcript, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
real_make_row = stop.make_row


def broken(*a, **k):
    raise RuntimeError("disk on fire")


stop.make_row = broken
try:
    code = stop.main({"cwd": repo2, "transcript_path": transcript, "session_id": "s"})
finally:
    stop.make_row = real_make_row
assert code == 2, code  # gate still blocks while tests fail

# 4. the ledger file is replaced whole, never left half-written, and no temp file remains
band = os.path.join(work, "band")
ledger.upsert_row({"project": "p", "session": "a", "timestamp": "t", "task": "x", "turns": 1, "input": 0,
                   "output": 0, "cache_read": 0, "cache_create": 0, "context_tokens": 0}, band)
ledger.upsert_row({"project": "p", "session": "b", "timestamp": "t", "task": "y", "turns": 1, "input": 0,
                   "output": 0, "cache_read": 0, "cache_create": 0, "context_tokens": 0}, band)
assert sorted(r["session"] for r in ledger.read_all(band)) == ["a", "b"]
assert not [f for f in os.listdir(band) if f.endswith(".tmp")]

# 5. subagents get their own read cache, separate from the main agent's
main_cache = read_dedup.cache_file("s1", None, None)
sub_cache = read_dedup.cache_file("s1", None, "agent-7")
assert main_cache != sub_cache

# 6. shared usage rules: partial last line waits, complete last line counts, repeats count once
t = os.path.join(work, "u.jsonl")
rec = lambda mid, n: json.dumps({"type": "assistant", "timestamp": "2026-11-01T00:00:00Z",  # noqa: E731
                                 "message": {"id": mid, "usage": {"input_tokens": n}}})
with open(t, "w", encoding="utf-8") as fh:
    fh.write(rec("a", 1) + "\n" + rec("b", 2) + "\n" + rec("b", 5) + "\n" + '{"type": "assist')
usage, offset = read_usage(t)
assert sum(v[1][0] for v in usage.values()) == 6 and len(usage) == 2, usage
with open(t, "a", encoding="utf-8") as fh:
    fh.write('ant"}\n')
usage, _ = read_usage(t)
assert len(usage) == 2  # the partial line did not count until it was whole and valid

# 7. git root is found by walking up, without running git
deep = os.path.join(repo, "a", "b")
os.makedirs(deep)
assert tests_gate.git_root(deep) == os.path.abspath(repo)

shutil.rmtree(work, ignore_errors=True)
print("fixes: all checks passed")
