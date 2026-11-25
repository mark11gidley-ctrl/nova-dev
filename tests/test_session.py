"""Self-check for session metrics and the pop-out page: python -I tests/test_session.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
work = tempfile.mkdtemp(prefix="nd-session-")
os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(work, "claude")
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state")

import report  # noqa: E402

t0 = dt.datetime(2026, 11, 24, 10, 0, 0, tzinfo=dt.timezone.utc)


def at(seconds):
    return (t0 + dt.timedelta(seconds=seconds)).isoformat()


def prompt(s, text="do the thing"):
    return json.dumps({"type": "user", "timestamp": at(s), "message": {"content": text}})


def reply(s, mid, inp=10, out=5, read=100):
    return json.dumps({"type": "assistant", "timestamp": at(s), "message": {"id": mid, "usage": {
        "input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read, "cache_creation_input_tokens": 0}}})


def tool_result(s):
    return json.dumps({"type": "user", "timestamp": at(s), "message": {"content": [
        {"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}})


# transcript: prompt at 0 s, replies up to 10 s; a tool result (not a prompt) at 12 s; reply at 15 s;
# a second prompt at 60 s with a reply at 65 s. Agent time = (15 - 0) + (65 - 60) = 20 s.
cwd = "C:/claudeobsidainai/nova-dev"
folder = os.path.join(work, "claude", "projects", "C--claudeobsidainai-nova-dev")
os.makedirs(folder)
path = os.path.join(folder, "abc123.jsonl")
with open(path, "w", encoding="utf-8") as fh:
    fh.write("\n".join([prompt(0), reply(5, "m1", 10, 5), reply(10, "m2", 10, 7), tool_result(12),
                        reply(15, "m3", 10, 3), prompt(60), reply(65, "m4", 10, 4)]) + "\n")

# the transcript path follows Claude Code's folder naming
assert report.transcript_path(cwd, "abc123") == path, report.transcript_path(cwd, "abc123")
assert report.transcript_path(cwd, "missing") is None

m = report.session_metrics(path)
assert m["agent_ms"] == 20_000, m  # the tool result does not start a new prompt
assert m["turns"] == 4 and m["output"] == 5 + 7 + 3 + 4, m
assert m["cache_read"] == 400 and m["input"] == 40, m
assert report.clock(m["agent_ms"]) == "20s" or report.clock(m["agent_ms"]) == "0m 20s", report.clock(m["agent_ms"])

# the cached metrics match the uncached ones, and a changed file is read again
assert report.session_metrics_cached(path) == m
assert report.session_metrics_cached(path) == m
with open(path, "a", encoding="utf-8") as fh:
    fh.write(reply(70, "m5", 1, 1, 1) + "\n")
assert report.session_metrics_cached(path)["turns"] == 5

# the pop-out page: built, local, shows agent time and the tests passed in
page_path = report.session_page(cwd, "abc123", cost="1.23", tests={"passed": 40, "failed": 0})
page = open(page_path, encoding="utf-8").read()
assert "Agent time" in page and "Session cost" in page and "$1.23" in page and "40 passed" in page
assert "http://" not in page and "https://" not in page and "<script" not in page

# avoided tokens and their cost: the page shows both, and the summary turns them into money at the input price
os.environ["NOVA_DEV_PRICE_INPUT"] = "3"
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state2")
import savings  # noqa: E402
savings.record("read", 4000)
summary = report.summary_data()
assert summary["saved_tokens"] == 1000 and abs(summary["saved_cost"] - 0.003) < 1e-12, summary
page = open(report.session_page(cwd, "abc123"), encoding="utf-8").read()
assert "Tokens you would have used" in page
assert "What those would have cost" in page

# the live page refreshes itself and has no external links
import live  # noqa: E402
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state3")
live_text = open(live.write_once(cwd, 7), encoding="utf-8").read()
assert 'http-equiv="refresh" content="7"' in live_text and "https://" not in live_text

shutil.rmtree(work, ignore_errors=True)
print("session: all checks passed")
