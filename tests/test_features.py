"""Self-check: python -I tests/test_features.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
work = tempfile.mkdtemp(prefix="nd-feat-")
os.environ["NOVA_DEV_DIR"] = work

from callers import find_callers  # noqa: E402
from testcheck import analyze  # noqa: E402
import ledger  # noqa: E402
from stats import collect  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

# callers: whole-word match, skips the excluded folders
src = os.path.join(work, "src")
os.makedirs(os.path.join(src, "node_modules"))
with open(os.path.join(src, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("def load_config():\n    return load_config_file()\n")
with open(os.path.join(src, "b.py"), "w", encoding="utf-8") as fh:
    fh.write("x = load_config()\n")
with open(os.path.join(src, "node_modules", "c.py"), "w", encoding="utf-8") as fh:
    fh.write("load_config()\n")
hits = find_callers("load_config", work)
assert sorted((h[0], h[1]) for h in hits) == [(os.path.join("src", "a.py"), 1), (os.path.join("src", "b.py"), 1)], hits

# testcheck: logic without tests fails; with a test passes; docs and binaries ignored
ok, added, _, _ = analyze("25\t0\tsrc/app.py\n", threshold=20)
assert not ok and added == 25
ok, _, tests, _ = analyze("25\t0\tsrc/app.py\n3\t0\ttests/test_app.py\n", threshold=20)
assert ok and tests == ["tests/test_app.py"]
ok, added, _, _ = analyze("50\t0\tREADME.md\n-\t-\tlogo.png\n5\t0\tsrc/x.py\n", threshold=20)
assert ok and added == 5
ok, _, _, _ = analyze("25\t0\tsrc/app.test.js\n", threshold=20)
assert ok  # a test file counts as the test

# band export: rows come back as JSON-able dicts; upsert keeps one row per session
tp = os.path.join(work, "s.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
    fh.write(json.dumps({"type": "assistant", "message": {"id": "m", "usage": {"input_tokens": 2}}}) + "\n")
base = os.path.join(work, "band")
ledger.upsert_row(ledger.make_row("sx", tp, "C:/p/proj"), base)
ledger.upsert_row(ledger.make_row("sx", tp, "C:/p/proj"), base)
rows = ledger.read_all(base)
assert len(rows) == 1 and rows[0]["input"] == "2", rows

# stats: collect honors the day window
base2 = os.path.join(work, "projects")
os.makedirs(os.path.join(base2, "p"))
now = datetime(2026, 11, 23, tzinfo=timezone.utc)
with open(os.path.join(base2, "p", "s.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "assistant", "sessionId": "s", "timestamp": (now - timedelta(days=2)).isoformat(),
                         "message": {"id": "m1", "usage": {"input_tokens": 7}}}) + "\n")
assert collect(base2, 1, now)["input"] == 0
assert collect(base2, 3, now)["input"] == 7

shutil.rmtree(work, ignore_errors=True)
print("features: all checks passed")
