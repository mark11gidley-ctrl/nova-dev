"""Self-check: python -I tests/test_security.py  (exits 0 on success)."""
import csv
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
work = tempfile.mkdtemp(prefix="nd-sec-")
os.environ["NOVA_DEV_DIR"] = work
for var in ("NOVA_DEV_WEBHOOK_TOKEN", "NOVA_DEV_SEND_NAMES", "NOVA_DEV_WEBHOOK_URL"):
    os.environ.pop(var, None)
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import settings  # noqa: E402
from redact import redact_text, line_kind  # noqa: E402
from secret_scan import scan, redact as redact_diff  # noqa: E402
from ledger import make_row  # noqa: E402
import band  # noqa: E402
import state  # noqa: E402
import read_dedup  # noqa: E402
import guard  # noqa: E402

# 1. webhook token comes only from the environment, never from the config file
with open(os.path.join(work, "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"webhook_token": "file-token-value-123"}, fh)
assert settings.get("webhook_token") == ""
os.environ["NOVA_DEV_WEBHOOK_TOKEN"] = "env-token-value-123"
assert settings.get("webhook_token") == "env-token-value-123"
assert "env-token-value-123" not in settings.summary() and "file-token-value-123" not in settings.summary()
os.environ.pop("NOVA_DEV_WEBHOOK_TOKEN")

# 2. task names are off by default (privacy)
assert settings.get("send_names") is False

# 3. secrets are redacted before they reach the ledger, the snapshot or a review
assert line_kind('password = "hunter2hunter2"') == "assigned secret"
assert "hunter2hunter2" not in redact_text('password = "hunter2hunter2"')
assert "[hidden: assigned secret]" in redact_text('password = "hunter2hunter2"')
tp = os.path.join(work, "s.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "message": {"content": "deploy with key = \"sk-abcdef123456\""}}) + "\n")
row = make_row("s", tp, "C:/p/proj")
assert "sk-abcdef123456" not in row["task"], row["task"]

diff = "+++ b/app.py\n@@ -0,0 +1,2 @@\n+x = 1\n+token = \"abcdefgh12345678\"\n"
assert redact_diff(diff.splitlines())[-1] == "+[line hidden: assigned secret]"
assert scan(diff) == [("app.py", 2, "assigned secret")]

# 4. CSV export neutralizes spreadsheet formulas
assert band._safe_cell("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")"
assert band._safe_cell("plain") == "plain"

# 5. caches live in the private state folder, not the shared temp folder
assert read_dedup.cache_file("abc").startswith(os.path.join(work, "cache"))
assert guard.cache_path("abc").startswith(os.path.join(work, "cache"))

# 6. files we write are owner-only where the OS supports it
probe = os.path.join(work, "private.txt")
state.write_private(probe, "x")
if os.name == "posix":
    assert stat.S_IMODE(os.stat(probe).st_mode) == 0o600

# 7. the webhook refuses plain http
import ledger  # noqa: E402
try:
    ledger.send_webhook({}, "http://example.com/hook")
    raise AssertionError("http accepted")
except ValueError:
    pass

# 8. the self-audit runs clean on the plugin's own code
audit = subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "scripts", "seccheck.py")],
                       capture_output=True, text=True)
assert audit.returncode == 0, audit.stdout

shutil.rmtree(work, ignore_errors=True)
print("security: all checks passed")
