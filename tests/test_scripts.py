"""Self-check: python -I tests/test_scripts.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from debt import scan  # noqa: E402
from stats import collect  # noqa: E402

# debt: finds comment-style shortcuts, ignores the same words in plain text
work = tempfile.mkdtemp(prefix="nd-debt-")
with open(os.path.join(work, "a.py"), "w", encoding="utf-8") as fh:
    fh.write("x = 1\n# shortcut: in-memory cache, move to Redis past 1k users\n")
    fh.write("the word shortcut: here is prose\n")
with open(os.path.join(work, "b.js"), "w", encoding="utf-8") as fh:
    fh.write("// ponytail: naive sort, fine under 100 rows\n")
hits = sorted(scan(work))
assert hits == [("a.py", 2, "in-memory cache, move to Redis past 1k users"),
                ("b.js", 1, "naive sort, fine under 100 rows")], hits
shutil.rmtree(work, ignore_errors=True)

# stats: streamed chunks counted once, old records excluded, cache rate correct
base = tempfile.mkdtemp(prefix="nd-stats-")
now = datetime(2026, 11, 23, tzinfo=timezone.utc)
recent = (now - timedelta(days=1)).isoformat().replace("+00:00", "Z")
old = (now - timedelta(days=90)).isoformat().replace("+00:00", "Z")

def rec(ts, mid, out):
    return json.dumps({"type": "assistant", "sessionId": "s1", "timestamp": ts,
                       "message": {"id": mid, "usage": {"input_tokens": 10, "output_tokens": out,
                                                        "cache_read_input_tokens": 90,
                                                        "cache_creation_input_tokens": 0}}})

proj = os.path.join(base, "proj")
os.makedirs(proj)
with open(os.path.join(proj, "s1.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(rec(recent, "m1", 5) + "\n")
    fh.write(rec(recent, "m1", 50) + "\n")   # same message, final chunk wins
    fh.write(rec(old, "m2", 999) + "\n")     # outside the window
totals = collect(base, 30, now)
assert totals["turns"] == 1, totals
assert totals["output"] == 50, totals
assert totals["input"] == 10 and totals["cache_read"] == 90, totals
shutil.rmtree(base, ignore_errors=True)

print("scripts: all checks passed")
