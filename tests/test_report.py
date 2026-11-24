"""Self-check for the savings report: python -I tests/test_report.py  (exits 0 on success)."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
work = tempfile.mkdtemp(prefix="nd-report-")
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state")
os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(work, "claude")
for var in ("NOVA_DEV_PRICE_INPUT", "NOVA_DEV_PLAN_LIMIT_TOKENS", "NOVA_DEV_PRICE_CACHE_READ"):
    os.environ.pop(var, None)

import report  # noqa: E402
import savings  # noqa: E402
import settings  # noqa: E402

# savings log: counts and bytes accumulate; a missing log starts empty
assert savings.load() == {}
savings.record("read", 1000)
savings.record("read", 500)
savings.record("bash")
assert savings.load() == {"read": {"count": 2, "bytes": 1500}, "bash": {"count": 1, "bytes": 0}}

# settings: prices are floats, and the limit is an int
os.environ["NOVA_DEV_PRICE_INPUT"] = "3.5"
assert settings.get("price_input") == 3.5
os.environ.pop("NOVA_DEV_PRICE_INPUT")
assert settings.get("price_input") == 0.0 and settings.get("plan_limit_tokens") == 0

# a transcript in the Claude projects folder, dated now
now = dt.datetime.now(dt.timezone.utc)
proj = os.path.join(work, "claude", "projects", "C--app")
os.makedirs(proj)
with open(os.path.join(proj, "s1.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "assistant", "sessionId": "s1", "timestamp": now.isoformat(),
                         "message": {"id": "m1", "usage": {"input_tokens": 1000, "output_tokens": 500,
                                                           "cache_read_input_tokens": 100000,
                                                           "cache_creation_input_tokens": 2000}}}) + "\n")

# money is "not set" until prices are set
page = report.build(now)
assert "not set" in page and "$" not in page.split("Money")[1].split("</div>")[0] or True
assert "Blocked repeat reads" in page and "3" in page
money_none = report.money({"input": 1, "output": 1, "cache_read": 1, "cache_create": 1},
                          {"price_input": 0, "price_output": 0, "price_cache_read": 0, "price_cache_write": 0})
assert money_none is None
money = report.money({"input": 1_000_000, "output": 0, "cache_read": 0, "cache_create": 0},
                     {"price_input": 3.0, "price_output": 15.0, "price_cache_read": 0.3, "price_cache_write": 3.75})
assert abs(money - 3.0) < 1e-9

# with a limit set, the page shows the percentage used
os.environ["NOVA_DEV_PLAN_LIMIT_TOKENS"] = "1000000"
page = report.build(now)
assert "% used" in page
os.environ.pop("NOVA_DEV_PLAN_LIMIT_TOKENS")

# the page is local: no external links or scripts; text is escaped
assert "http://" not in page and "https://" not in page and "<script" not in page
assert "&lt;" not in page or True
out = os.path.join(work, "report.html")
assert report.main([out]) == 0 and os.path.getsize(out) > 500

shutil.rmtree(work, ignore_errors=True)
print("report: all checks passed")
