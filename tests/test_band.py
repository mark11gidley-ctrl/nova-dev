"""Self-check: python -I tests/test_band.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
work = tempfile.mkdtemp(prefix="nd-band-")
os.environ["NOVA_DEV_DIR"] = work

import ledger  # noqa: E402
from ledger import build_payload, make_row, read_all, send_webhook, upsert_row  # noqa: E402
from tests_gate import status  # noqa: E402
from context_watch import autocompact_block  # noqa: E402
import build_adapters  # noqa: E402
import debt  # noqa: E402
from band import as_markdown, board_html  # noqa: E402
from state import get_level  # noqa: E402

# transcript with a streamed message (same id twice) and a user prompt
tp = os.path.join(work, "s1.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "message": {"content": "Fix the <b>login</b> bug"}}) + "\n")
    fh.write(json.dumps({"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 1, "output_tokens": 5,
             "cache_read_input_tokens": 10, "cache_creation_input_tokens": 0}}}) + "\n")
    fh.write(json.dumps({"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 1, "output_tokens": 50,
             "cache_read_input_tokens": 10, "cache_creation_input_tokens": 0}}}) + "\n")
t = ledger.session_totals(tp)
assert t["turns"] == 1 and t["output"] == 50 and t["context_tokens"] == 11, t
row = make_row("s1", tp, "C:/x/myproj")
assert row["project"] == "myproj" and row["task"] == "Fix the <b>login</b> bug"

# one row per session: upsert replaces, does not duplicate
base = os.path.join(work, "band")
upsert_row(row, base)
row2 = dict(row, output=99)
upsert_row(row2, base)
rows = read_all(base)
assert len(rows) == 1 and rows[0]["output"] == "99", rows

# webhook: https only, bearer token sent, names optional
assert "task" not in build_payload(row, False)
assert build_payload(row, True)["task"] == row["task"]
try:
    send_webhook({}, "http://insecure.example")
    raise AssertionError("http accepted")
except ValueError:
    pass
captured = {}

class FakeResp:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False

def fake_open(req, timeout):
    captured["auth"] = req.get_header("Authorization")
    captured["body"] = json.loads(req.data)
    return FakeResp()

assert send_webhook(build_payload(row, True), "https://example.com/hook", "tok", opener=fake_open)
assert captured["auth"] == "Bearer tok" and captured["body"]["session"] == "s1"

# board and markdown escape user text
html_out = board_html(read_all(base))
assert "&lt;b&gt;login&lt;/b&gt;" in html_out and "<b>login</b>" not in html_out
assert "Fix the" in as_markdown(row)

# tests gate: failing fresh log -> fail; passing -> pass; stale -> None
repo = os.path.join(work, "repo")
os.makedirs(os.path.join(repo, ".claude"))
import subprocess  # noqa: E402
subprocess.run(["git", "init", "-q", repo], check=True)
log = os.path.join(repo, ".claude", "last_test_output.txt")
with open(log, "w", encoding="utf-8") as fh:
    fh.write(" Tests  2 failed | 5 passed (7)\n")
assert status(repo) == "fail"
with open(log, "w", encoding="utf-8") as fh:
    fh.write(" Tests  7 passed (7)\n")
assert status(repo) == "pass"
assert status(repo, now=time.time() + 3600) is None

# auto-compact: opt-in only, blocks once per debounce window
os.environ.pop("NOVA_DEV_AUTOCOMPACT", None)
assert autocompact_block("a", 999_999) is None
os.environ["NOVA_DEV_AUTOCOMPACT"] = "1"
os.environ["NOVA_DEV_WINDOW"] = "100"
assert autocompact_block("a", 10) is None
assert "/compact" in autocompact_block("a", 60)
assert autocompact_block("a", 60) is None
os.environ.pop("NOVA_DEV_AUTOCOMPACT")
os.environ.pop("NOVA_DEV_WINDOW")

# default level from env, file wins over env
os.environ["NOVA_DEV_DEFAULT"] = "ultra"
assert get_level() == "ultra"
os.environ.pop("NOVA_DEV_DEFAULT")

# adapters: every target written, all contain the core rules
out_root = os.path.join(work, "adapters")
files = build_adapters.build(out_root)
assert len(files) == 7
for f in files:
    assert "least code" in open(f, encoding="utf-8").read(), f

# debt: custom marker word
with open(os.path.join(work, "c.py"), "w", encoding="utf-8") as fh:
    fh.write("# todo: rewrite later, fine for now\n")
assert [h[2] for h in debt.scan(work, "todo")] == ["rewrite later, fine for now"]

shutil.rmtree(work, ignore_errors=True)
print("band and features: all checks passed")
