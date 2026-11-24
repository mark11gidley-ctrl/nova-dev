"""Self-check for the token-saving features: python -I tests/test_tokensave.py  (exits 0 on success)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
work = tempfile.mkdtemp(prefix="nd-tok-")
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state")
os.environ.pop("NOVA_DEV_RULES_STYLE", None)

import cache_guard  # noqa: E402
import runtests  # noqa: E402
import savings_show  # noqa: E402
import savings  # noqa: E402

# 1. cache-break warning: always-on files warn once per session; ordinary files never warn
agents = {"session_id": "s1", "tool_input": {"file_path": os.path.join(work, "AGENTS.md")}}
assert cache_guard.advice(agents) is not None
assert cache_guard.advice(agents) is None  # once per session
assert cache_guard.advice({"session_id": "s1", "tool_input": {"file_path": os.path.join(work, "app.py")}}) is None
core = {"session_id": "s2", "tool_input": {"file_path": os.path.join(work, "rules", "core.md")}}
assert cache_guard.advice(core) is not None

# 2. short rules: one line per level, shorter than the full rules
import settings  # noqa: E402
os.environ["NOVA_DEV_RULES_STYLE"] = "short"
assert settings.get("rules_style") == "short"
os.environ.pop("NOVA_DEV_RULES_STYLE")
assert settings.get("rules_style") == "full"

# 3. cached test result: reused only when nothing changed since it was written
repo = os.path.join(work, "repo")
os.makedirs(repo)
subprocess.run(["git", "init", "-q", repo], check=True)
src = os.path.join(repo, "app.py")
open(src, "w", encoding="utf-8").write("x = 1\n")
past = time.time() - 3600
os.utime(src, (past, past))
subprocess.run(["git", "-C", repo, "add", "."], check=True)
subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init"],
               check=True)
os.utime(src, (past, past))
os.makedirs(os.path.join(repo, ".claude"))
log = os.path.join(repo, ".claude", "last_test_output.txt")
open(log, "w", encoding="utf-8").write("ok\nnova-dev: RESULT pass\n")
assert runtests.cached_result(repo) is not None and runtests.cached_result(repo)[0] == 0
time.sleep(0.05)
open(src, "w", encoding="utf-8").write("x = 2\n")  # a change after the log
assert runtests.cached_result(repo) is None
os.utime(log, (past - 10, past - 10))  # an older log than the change: not reused
assert runtests.cached_result(repo) is None
open(log, "w", encoding="utf-8").write("bad\nnova-dev: RESULT fail\n")
assert runtests.cached_result(repo) is None or runtests.cached_result(repo)[0] == 1

# 4. savings command: empty and filled
assert savings_show.lines({}) == ["no savings recorded yet"]
savings.record("read", 400)
assert "repeat reads blocked" in savings_show.lines()[0]

shutil.rmtree(work, ignore_errors=True)
print("token saving: all checks passed")
