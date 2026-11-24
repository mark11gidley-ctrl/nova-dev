"""Self-check: python -I tests/test_context_tools.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
work = tempfile.mkdtemp(prefix="nd-ctx-")

from outline import outline  # noqa: E402
from logsum import summarize  # noqa: E402
from diffcompress import compress  # noqa: E402
from toolcost import analyze as toolcost_analyze  # noqa: E402
from contexthist import history  # noqa: E402
from secret_scan import scan as secret_scan  # noqa: E402
from restore import restore_text  # noqa: E402
from bigread import decide as bigread_decide  # noqa: E402
from init import init  # noqa: E402

# outline: definitions and headings with line numbers
code = "import os\n\ndef alpha():\n    pass\n\nclass Beta:\n    pass\n"
out = outline(code)
assert out[0].startswith("3: def alpha") and out[1].startswith("6: class Beta"), out

# logsum: failing lines kept with context, long passing runs dropped
log = "\n".join([f"ok {i}" for i in range(100)] + ["FAILED test_x", "assert 1 == 2"] + [f"ok {i}" for i in range(100)])
summary = summarize(log, cap=60, tail=2)
assert summary[0].startswith("202 lines") and any("FAILED test_x" in s for s in summary)
assert not any("ok 10:" in s for s in summary)

# diffcompress: caps changed lines per file and says how many were dropped
diff = "diff --git a/x b/x\n+++ b/x\n@@ -1 +1 @@\n" + "\n".join(f"+line {i}" for i in range(10))
small = compress(diff, cap=3)
assert sum(1 for s in small if s.startswith("+line")) == 3 and "7 more changed lines" in small[-1], small

# toolcost: sizes per tool name, repeated reads flagged
tp = os.path.join(work, "t.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "1", "name": "Read", "input": {"file_path": "a.py"}}]}}) + "\n")
    fh.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "1", "content": "x" * 500}]}}) + "\n")
    fh.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "2", "name": "Read", "input": {"file_path": "a.py"}}]}}) + "\n")
    fh.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "2", "content": "y" * 100}]}}) + "\n")
per_tool, repeats = toolcost_analyze(tp)
assert per_tool["Read"] == (2, 600), per_tool
assert repeats == {"a.py": 2}, repeats

# contexthist: same message id counts once; jumps are flagged
assert history(tp) == []  # no usage records in this file
with open(tp, "w", encoding="utf-8") as fh:
    for mid, ctx in (("a", 1000), ("b", 50000), ("b", 60000)):
        fh.write(json.dumps({"type": "assistant", "message": {"id": mid, "usage": {"input_tokens": ctx}}}) + "\n")
assert history(tp) == [1000, 60000], history(tp)

# secrets: finds the kind and line, never the value
diff2 = ("diff --git a/cfg.py b/cfg.py\n+++ b/cfg.py\n@@ -1,1 +1,2 @@\n x = 1\n"
         "+API_KEY = \"abcdefgh12345678\"\n")
found = secret_scan(diff2)
assert found == [("cfg.py", 2, "assigned secret")], found
assert secret_scan("+++ b/a.py\n@@ -0,0 +1 @@\n+print('hello')\n") == []

# restore: only after compaction, capped
proj = os.path.join(work, "proj")
os.makedirs(os.path.join(proj, ".claude"))
with open(os.path.join(proj, ".claude", "CONTEXT-SNAPSHOT.md"), "w", encoding="utf-8") as fh:
    fh.write("goal: fix login\n" + "z" * 10000)
assert restore_text({"source": "startup", "cwd": proj}) == ""
txt = restore_text({"source": "compact", "cwd": proj})
assert "goal: fix login" not in txt and "truncated" in txt and len(txt) < 6200

# bigread: off by default, blocks long whole-file reads, passes ranged reads
big = os.path.join(work, "big.txt")
with open(big, "w", encoding="utf-8") as fh:
    fh.write("line\n" * 50)
assert bigread_decide({"tool_input": {"file_path": big}}, 0)[0] == 0
assert bigread_decide({"tool_input": {"file_path": big}}, 10)[0] == 2
assert bigread_decide({"tool_input": {"file_path": big, "offset": 5}}, 10)[0] == 0
assert bigread_decide({"tool_input": {"file_path": big}}, 100)[0] == 0

# init: writes config once, never overwrites, adds git ignores only in git repos
ip = os.path.join(work, "app")
os.makedirs(os.path.join(ip, ".git"))
actions = init(ip, "lite")
assert json.load(open(os.path.join(ip, ".claude", "nova-dev.json")))["level"] == "lite"
assert "CONTEXT-SNAPSHOT" in open(os.path.join(ip, ".gitignore"), encoding="utf-8").read()
assert init(ip, "ultra")[0] == "kept existing .claude/nova-dev.json"
assert json.load(open(os.path.join(ip, ".claude", "nova-dev.json")))["level"] == "lite"
plain = os.path.join(work, "plain")
os.makedirs(plain)
assert init(plain, "full")[-1] == "not a git repository: .gitignore left alone"

shutil.rmtree(work, ignore_errors=True)
print("context tools: all checks passed")
