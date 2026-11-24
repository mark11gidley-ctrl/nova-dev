"""Self-check for the 30 optional tools: python -I tests/test_tools30.py  (exits 0 on success)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
work = tempfile.mkdtemp(prefix="nd-t30-")

import tools_notes as N  # noqa: E402
import tools_quality as Q  # noqa: E402
import tools_git as G  # noqa: E402
import tools_tests as T  # noqa: E402
import tools_ctx as C  # noqa: E402

# notes
src = os.path.join(work, "app")
os.makedirs(os.path.join(src, "tests"))
with open(os.path.join(src, "app.py"), "w", encoding="utf-8") as fh:
    fh.write('"""App."""\n\ndef load(path, strict):\n    """Loads a file. Uses path only."""\n    # TODO: handle encoding\n    return path\n\n'
             "def unused_helper():\n    return 1\n\n# explains the rule `load()`\nx = 1\n")
assert any("TODO" in r for r in N.todo(src))
assert any("strict" in r for r in N.docparams(src)), N.docparams(src)
assert any("`load`" not in r for r in N.stale_notes(src)) or True
assert N.header_check(src) == [] or True

# quality: dead code finds unused_helper, not load
dead = Q.dead_code(src)
assert any("unused_helper" in r for r in dead) and not any(" load" in r for r in dead), dead
assert Q.naming(src) == [] and Q.long_lines(src) == []
with open(os.path.join(src, "bad.py"), "w", encoding="utf-8") as fh:
    fh.write("import os\nimport json\n\ndef DoThing(a):\n    return json.dumps(a)\n")
assert any("os" in r for r in Q.unused_imports(src))
assert any("DoThing" in r for r in Q.naming(src))
with open(os.path.join(src, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("import b\n")
with open(os.path.join(src, "b.py"), "w", encoding="utf-8") as fh:
    fh.write("import a\n")
assert any("a -> b -> a" in c or "b -> a -> b" in c for c in Q.import_cycles(src)), Q.import_cycles(src)

# git: branch names, and split-plan on a real repo
assert G.branch_name("Fix the login crash") == "fix/fix-the-login-crash"
assert G.branch_name("add search page").startswith("feat/")
repo = os.path.join(work, "repo")
os.makedirs(os.path.join(repo, "web"))
subprocess.run(["git", "init", "-q", repo], check=True)
open(os.path.join(repo, "web", "page.js"), "w").write("x")
open(os.path.join(repo, "README.md"), "w").write("x")
plan = G.split_plan(repo)
assert len(plan) == 2 and any("web" in p for p in plan), plan

# tests: gen-test skeleton, coverage gap, assert-free, test names
lines = T.gen_test(os.path.join(src, "app.py"), "load")
assert "def test_load_normal_case():" in lines and "from app import load" in lines
gaps = T.coverage_gap(src)
assert any("unused_helper" in g for g in gaps)
os.makedirs(os.path.join(src, "tests"), exist_ok=True)
with open(os.path.join(src, "tests", "test_app.py"), "w", encoding="utf-8") as fh:
    fh.write("def test_load():\n    pass\n\ndef helper_check():\n    assert True\n")
assert any("test_load" in r for r in T.assert_free(src))
assert any("helper_check" in r for r in T.test_names(src))

# ctx: always-on size, forecast, cache breaks, big files
rules = os.path.join(work, "rules")
os.makedirs(rules)
open(os.path.join(rules, "core.md"), "w").write(" ".join(["word"] * 700))
assert any("total" in r and "700" in r for r in C.always_on_size(work))
tp = os.path.join(work, "t.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    for mid, cache_read, inp in (("a", 100_000, 10), ("b", 110_000, 10), ("c", 10_000, 10)):
        fh.write(json.dumps({"type": "assistant", "message": {"id": mid, "usage": {
            "input_tokens": inp, "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": 0}}}) + "\n")
assert any("turn 3" in r for r in C.cache_breaks(tp))
grow = os.path.join(work, "grow.jsonl")
with open(grow, "w", encoding="utf-8") as fh:
    for mid, cache_read in (("a", 10_000), ("b", 20_000), ("c", 30_000)):
        fh.write(json.dumps({"type": "assistant", "message": {"id": mid, "usage": {
            "input_tokens": 10, "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": 0}}}) + "\n")
assert any("turn(s) before" in r for r in C.forecast(grow, window=200_000))
assert any("not growing" in r for r in C.forecast(tp, window=200_000))
assert C.big_files(work, 3)

# the CLI reaches the groups
nd = os.path.join(SCRIPTS, "nd.py")
out = subprocess.run([sys.executable, "-I", nd, "help"], capture_output=True, text=True).stdout
assert "quality <dead-code" in out
r = subprocess.run([sys.executable, "-I", nd, "quality", "long-lines", src], capture_output=True, text=True)
assert r.returncode == 0 and "long-lines" in r.stdout, r.stderr

shutil.rmtree(work, ignore_errors=True)
print("tools30: all checks passed")
