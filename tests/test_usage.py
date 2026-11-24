"""Self-check for the usage tools: python -I tests/test_usage.py  (exits 0 on success)."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
work = tempfile.mkdtemp(prefix="nd-usage-")
os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(work, "claude")
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state")
os.environ["NOVA_DEV_PLAN_LIMIT_TOKENS"] = "1000"
for var in ("NOVA_DEV_PRICE_INPUT", "NOVA_DEV_PRICE_OUTPUT", "NOVA_DEV_PRICE_CACHE_READ", "NOVA_DEV_PRICE_CACHE_WRITE"):
    os.environ.pop(var, None)

import tools_usage as U  # noqa: E402

now = dt.datetime.now(dt.timezone.utc)
two_days = now - dt.timedelta(days=2)


def turn(ts, mid, inp, out, read, create=0, model="claude-test", side=False):
    return json.dumps({"type": "assistant", "sessionId": "x", "timestamp": ts.isoformat(), "isSidechain": side,
                       "message": {"id": mid, "model": model, "usage": {
                           "input_tokens": inp, "output_tokens": out,
                           "cache_read_input_tokens": read, "cache_creation_input_tokens": create}}})


def write(project, session, lines):
    folder = os.path.join(work, "claude", "projects", project)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, session + ".jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# project A: session a1 has a cache break (read drops from 90000 to 1000); a streamed message counted once
write("proj-a", "a1", [
    turn(two_days, "m1", 10, 5, 0, 90000),
    turn(two_days + dt.timedelta(minutes=1), "m2", 10, 5, 90000),
    turn(two_days + dt.timedelta(minutes=2), "m2", 10, 50, 90000),        # same message, final chunk wins
    turn(two_days + dt.timedelta(minutes=3), "m3", 10, 5, 1000),          # break
])
# project B: a subagent turn on a different model
write("proj-b", "b1", [
    turn(two_days, "n1", 100, 100, 0, model="claude-big", side=True),
])
# three sessions in project C that grow at different rates, for context-alert
for s, step in (("c1", 1000), ("c2", 1000), ("c3", 9000)):
    write("proj-c", s, [turn(two_days + dt.timedelta(minutes=i), f"{s}-{i}", 10, 5, step * i) for i in range(1, 4)])

# project costs: tokens and sessions per project, and "not set" money with no prices
rows = U.project_costs(30)
assert any("proj-a" in r and "not set" in r for r in rows), rows
a = next(r for r in rows if "proj-a" in r)
assert "1 session(s)" in a

# cache efficiency: one break in proj-a
rows = U.cache_efficiency(30)
assert any("proj-a" in r and "1 break(s)" in r for r in rows), rows

# model mix and subagent share
mix = U.model_mix(30)
assert any("claude-big" in r for r in mix)
share = U.subagent_share(30)
assert "subagents" in share[1] and "main conversation" in share[0]

# limit burn-down: 1000-token limit and the window's usage gives a days-left estimate
rows = U.limit_burndown(7)
assert any("% of 1,000 tokens" in r for r in rows), rows

# idle sessions: nothing recent in this window is idle and large, so the message says so
rows = U.idle_sessions(24)
assert rows and ("no idle session" in rows[0] or "idle" in rows[0])

# context alert: c3 grows far faster than the others
rows = U.context_alert(30)
assert any("session c3" in r for r in rows), rows

# task estimate: needs ledger rows
os.makedirs(os.path.join(work, "state", "band"), exist_ok=True)
with open(os.path.join(work, "state", "band", "p.csv"), "w", encoding="utf-8") as fh:
    fh.write("timestamp,project,session,task,turns,input,output,cache_read,cache_create,context_tokens\n")
    fh.write("2026-11-01T00:00:00,p,s1,Fix the login bug,3,10,10,100,0,110\n")
assert "1 matching task" in U.task_estimate("login")[0]
assert "no recorded task" in U.task_estimate("zzz")[0]

# weekly summary writes a Markdown file
out = os.path.join(work, "weekly.md")
assert "weekly summary" in U.weekly_summary(out)[0] and os.path.getsize(out) > 100

# CLI dispatch
assert U.main(["bogus"]) == 2
assert U.main(["task-estimate"]) == 2

shutil.rmtree(work, ignore_errors=True)
print("usage tools: all checks passed")
