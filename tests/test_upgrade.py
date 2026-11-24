"""Self-check: python -I tests/test_upgrade.py  (exits 0 on success)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
work = tempfile.mkdtemp(prefix="nd-up-")
os.environ["NOVA_DEV_DIR"] = work
for var in ("NOVA_DEV_WINDOW", "NOVA_DEV_CONTEXT_WARN", "NOVA_DEV_WEBHOOK_TOKEN", "NOVA_DEV_DEFAULT"):
    os.environ.pop(var, None)
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import settings  # noqa: E402
from prompt_submit import decide  # noqa: E402
from find_session import find  # noqa: E402
from review import bundle  # noqa: E402

# settings: default, then config file, then env wins over file
assert settings.get("context_warn") == 150_000
with open(os.path.join(work, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"context_warn": 100, "autocompact": "yes", "webhook_token": "s3cret-token"}, fh)
assert settings.get("context_warn") == 100
assert settings.get("autocompact") is True
os.environ["NOVA_DEV_CONTEXT_WARN"] = "42"
assert settings.get("context_warn") == 42
os.environ["NOVA_DEV_CONTEXT_WARN"] = "not-a-number"   # bad env falls back to file
assert settings.get("context_warn") == 100
os.environ.pop("NOVA_DEV_CONTEXT_WARN")
summary = settings.summary()
assert "s3cret-token" not in summary and "webhook_token: not set" in summary, summary  # file tokens are ignored

# /nova-dev status is answered from settings and never shows the token
status = decide("/nova-dev status")
assert "level (this folder)" in status and "s3cret-token" not in status, status

# review bundle: secrets and tests reported, verdict set
diff = ("diff --git a/a.py b/a.py\n+++ b/a.py\n@@ -0,0 +1,2 @@\n+x = 1\n"
        "+KEY = \"abcdefgh12345678\"\n")
numstat = "2\t0\ta.py\n"
out = bundle(diff, numstat, threshold=1)
assert "assigned secret" in out and "needs attention" in out, out
assert "abcdefgh12345678" not in out  # never print the value
clean = bundle("", "", threshold=20)
assert "(no changes)" in clean and "clean" in clean

# find: searches only user prompts, newest first
proj = os.path.join(work, "projects", "C--app")
os.makedirs(proj)
with open(os.path.join(proj, "abc.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "timestamp": "2026-11-01T10:00:00Z",
                         "message": {"content": "Fix the webhook retry bug"}}) + "\n")
    fh.write(json.dumps({"type": "assistant", "timestamp": "2026-11-01T10:01:00Z",
                         "message": {"content": "webhook retry is fine"}}) + "\n")
rows = find(os.path.join(work, "projects"), "webhook")
assert len(rows) == 1 and rows[0][1] == "abc" and "retry bug" in rows[0][3], rows

# nd.py: status works, unknown command exits 2, doctor runs through the CLI
nd = os.path.join(HERE, "..", "scripts", "nd.py")
py = sys.executable
assert subprocess.run([py, "-I", nd, "status"], capture_output=True, text=True).returncode == 0
assert subprocess.run([py, "-I", nd, "nope"], capture_output=True, text=True).returncode == 2
assert "CLAUDE_PLUGIN_ROOT" not in subprocess.run([py, "-I", nd, "help"], capture_output=True, text=True).stdout

shutil.rmtree(work, ignore_errors=True)
print("upgrade: all checks passed")
