"""Usage and money tools, read from your transcripts and the band ledger. Usage: nd.py usage <name> [args]

  project-costs [days]           tokens and estimated cost per project
  limit-burndown [days]          daily use against your plan limit, and when it runs out at this pace
  idle-sessions [hours]          sessions untouched for a while that still hold a large context
  cache-efficiency [days]        cache hit rate and cache breaks, per project
  task-estimate <words>          typical tokens for tasks whose name contains the words (from the band ledger)
  context-alert [days]           sessions whose context grows much faster than the typical session
  tool-hogs [days]               which tools return the most output, across all sessions
  model-mix [days]               tokens per model
  subagent-share [days]          tokens spent in subagents versus the main conversation
  weekly-summary [file.md]       one Markdown page for the last 7 days

Money is an estimate at the prices you set in config.json; with no prices set it says so.
Read-only. Token numbers come from the transcripts, not estimates.
"""
import datetime as dt
import glob
import hashlib
import json
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, HERE)
import ledger  # noqa: E402
import savings  # noqa: E402
import settings  # noqa: E402
from state import state_dir  # noqa: E402
from stats import projects_dir  # noqa: E402
from toolcost import analyze as tool_analyze  # noqa: E402

PRICES = ("price_input", "price_output", "price_cache_read", "price_cache_write")


def parse_ts(text):
    try:
        return dt.datetime.fromisoformat((text or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_file(path):
    """All assistant turns in one transcript, one per message (streamed chunks counted once), as plain data."""
    project = os.path.basename(os.path.dirname(path))
    session = os.path.splitext(os.path.basename(path))[0]
    seen = {}
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            u = msg.get("usage")
            ts = parse_ts(rec.get("timestamp"))
            if rec.get("type") != "assistant" or not u or ts is None:
                continue
            key = msg.get("id") or rec.get("uuid")
            seen.pop(key, None)
            seen[key] = {
                "project": project, "session": session, "ts": ts.isoformat(),
                "model": msg.get("model") or "unknown", "sidechain": bool(rec.get("isSidechain")),
                "u": [u.get("input_tokens", 0) or 0, u.get("output_tokens", 0) or 0,
                      u.get("cache_read_input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0],
            }
    return list(seen.values())


def _file_turns(path):
    """Turns for one file, from a cache that is rebuilt only when the file's size or modification time changes."""
    st = os.stat(path)
    digest = hashlib.sha256(os.path.abspath(path).encode("utf-8")).hexdigest()[:24]
    cache_path = os.path.join(state_dir(), "cache", f"turns-{digest}.json")
    try:
        with open(cache_path, encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("size") == st.st_size and cached.get("mtime") == st.st_mtime_ns:
            return cached["records"]
    except (OSError, ValueError, KeyError):
        pass
    records = _parse_file(path)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump({"size": st.st_size, "mtime": st.st_mtime_ns, "records": records}, fh)
    return records


def turns(days, now=None):
    """Every assistant turn in the window, oldest first. Files are read from the cache when unchanged."""
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days)
    out = []
    for path in glob.glob(os.path.join(projects_dir(), "**", "*.jsonl"), recursive=True):
        if os.path.getmtime(path) < cutoff.timestamp():
            continue
        for rec in _file_turns(path):
            ts = parse_ts(rec["ts"])
            if ts is not None and ts >= cutoff:
                out.append(dict(rec, ts=ts, u=tuple(rec["u"])))
    return sorted(out, key=lambda t: t["ts"])


def total(u):
    return sum(u)


def cost(u, prices):
    i, o, r, c = u
    return (i * prices["price_input"] + o * prices["price_output"] + r * prices["price_cache_read"]
            + c * prices["price_cache_write"]) / 1_000_000


def prices():
    return {k: float(settings.get(k)) for k in PRICES}


def money_text(value, p):
    if not any(p.values()):
        return "not set"
    return f"${value:,.2f}"


def fmt(n):
    return f"{int(n):,}"


# ---- tools ----

def project_costs(days=30):
    p = prices()
    per = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "sessions": set()})
    for t in turns(days):
        row = per[t["project"]]
        row["tokens"] += total(t["u"])
        row["cost"] += cost(t["u"], p)
        row["sessions"].add(t["session"])
    rows = sorted(per.items(), key=lambda kv: kv[1]["tokens"], reverse=True)[:20]
    out = [f"{fmt(v['tokens']):>16} tokens  {money_text(v['cost'], p):>10}  {len(v['sessions']):>3} session(s)  {k}"
           for k, v in rows]
    return out or ["no usage in this window"]


def limit_burndown(days=7):
    limit = int(settings.get("plan_limit_tokens") or 0)
    daily = defaultdict(int)
    for t in turns(days):
        daily[t["ts"].date().isoformat()] += total(t["u"])
    if not daily:
        return ["no usage in this window"]
    used = sum(daily.values())
    out = [f"{d}  {fmt(v)} tokens" for d, v in sorted(daily.items())]
    if not limit:
        return out + [f"total {fmt(used)} tokens; set plan_limit_tokens in config.json to see the burn-down"]
    pace = used / len(daily)
    left = max(0, limit - used)
    days_left = left / pace if pace else float("inf")
    out.append(f"used {used / limit * 100:.1f}% of {fmt(limit)} tokens over {days} days")
    out.append(f"at {fmt(pace)} tokens a day, the limit runs out in about {days_left:.1f} day(s)")
    return out


def idle_sessions(hours=24):
    window = int(settings.get("window"))
    now = dt.datetime.now(dt.timezone.utc)
    last = {}
    for t in turns(30, now):
        last[t["session"]] = t
    rows = []
    for s, t in last.items():
        idle = (now - t["ts"]).total_seconds() / 3600
        context = t["u"][0] + t["u"][2] + t["u"][3]
        if idle >= float(hours) and context >= window * 0.5:
            rows.append(f"{t['project']}  session {s[:8]}  idle {idle:.0f} h  context {fmt(context)} tokens")
    return rows or [f"no idle session holds more than half the window ({fmt(window // 2)} tokens)"]


def cache_efficiency(days=30):
    per = defaultdict(lambda: {"prompt": 0, "read": 0, "breaks": 0})
    prev = {}
    for t in turns(days):
        i, o, r, c = t["u"]
        row = per[t["project"]]
        row["prompt"] += i + r + c
        row["read"] += r
        before = prev.get(t["session"])
        if before and before > 0 and r < before * 0.5:
            row["breaks"] += 1
        prev[t["session"]] = r
    rows = []
    for name, v in sorted(per.items(), key=lambda kv: kv[1]["prompt"], reverse=True)[:20]:
        hit = v["read"] / v["prompt"] * 100 if v["prompt"] else 0
        rows.append(f"{hit:5.1f}% hit  {v['breaks']:>3} break(s)  {name}")
    return rows or ["no usage in this window"]


def task_estimate(words):
    needle = words.lower()
    matches = [r for r in ledger.read_all() if needle in (r.get("task") or "").lower()]
    if not matches:
        return [f"no recorded task contains '{words}'"]
    totals = [sum(int(float(r[k] or 0)) for k in ("input", "output", "cache_read", "cache_create")) for r in matches]
    return [f"{len(matches)} matching task(s)", f"typical: {fmt(statistics.median(totals))} tokens (median)",
            f"range: {fmt(min(totals))} to {fmt(max(totals))} tokens"]


def context_alert(days=30):
    sessions = defaultdict(list)
    for t in turns(days):
        i, _o, r, c = t["u"]
        sessions[t["session"]].append((t["project"], i + r + c))
    growth = {}
    for s, pts in sessions.items():
        if len(pts) >= 3:
            growth[s] = ((pts[-1][1] - pts[0][1]) / (len(pts) - 1), pts[0][0])
    if len(growth) < 3:
        return ["need at least three sessions with three turns each"]
    typical = statistics.median(g for g, _ in growth.values())
    rows = [f"{proj}  session {s[:8]}  grows {g:,.0f} tokens per turn (typical {typical:,.0f})"
            for s, (g, proj) in sorted(growth.items(), key=lambda kv: kv[1][0], reverse=True)
            if typical > 0 and g > 2 * typical][:20]
    return rows or ["no session grows faster than twice the typical rate"]


def tool_hogs(days=30):
    cutoff = dt.datetime.now().timestamp() - days * 86400
    totals = defaultdict(lambda: [0, 0])
    for path in glob.glob(os.path.join(projects_dir(), "**", "*.jsonl"), recursive=True):
        if os.path.getmtime(path) < cutoff:
            continue
        per_tool, _repeats = tool_analyze(path)
        for name, (calls, chars) in per_tool.items():
            totals[name][0] += calls
            totals[name][1] += chars
    rows = sorted(totals.items(), key=lambda kv: kv[1][1], reverse=True)[:15]
    return [f"{fmt(chars):>14} chars  {calls:>6} call(s)  {name}" for name, (calls, chars) in rows] or ["no tool output found"]


def model_mix(days=30):
    per = defaultdict(int)
    for t in turns(days):
        per[t["model"]] += total(t["u"])
    grand = sum(per.values()) or 1
    return [f"{v / grand * 100:5.1f}%  {fmt(v):>16} tokens  {k}" for k, v in sorted(per.items(), key=lambda kv: kv[1], reverse=True)] \
        or ["no usage in this window"]


def subagent_share(days=30):
    main = sub = 0
    for t in turns(days):
        if t["sidechain"]:
            sub += total(t["u"])
        else:
            main += total(t["u"])
    grand = main + sub
    if not grand:
        return ["no usage in this window"]
    return [f"main conversation: {fmt(main)} tokens ({main / grand * 100:.1f}%)",
            f"subagents:         {fmt(sub)} tokens ({sub / grand * 100:.1f}%)"]


def weekly_summary(path=None):
    path = path or os.path.join(state_dir(), "weekly.md")
    week = turns(7)
    p = prices()
    tokens = sum(total(t["u"]) for t in week)
    money = sum(cost(t["u"], p) for t in week)
    sessions = len({t["session"] for t in week})
    lines = ["# Week summary", "", f"- Tokens: {fmt(tokens)}",
             f"- Estimated cost: {money_text(money, p)}", f"- Sessions: {sessions}", "", "## Projects"]
    lines += [f"- {r}" for r in project_costs(7)[:5]]
    lines += ["", "## Models"] + [f"- {r}" for r in model_mix(7)]
    lines += ["", "## Savings (all time)"]
    data = savings.load()
    lines.append(f"- Repeat reads blocked: {data.get('read', {}).get('count', 0)}")
    lines.append(f"- Repeat commands blocked: {data.get('bash', {}).get('count', 0)}")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return [f"weekly summary -> {path}"]


COMMANDS = {
    "project-costs": (project_costs, 30), "limit-burndown": (limit_burndown, 7),
    "idle-sessions": (idle_sessions, 24), "cache-efficiency": (cache_efficiency, 30),
    "task-estimate": (task_estimate, None), "context-alert": (context_alert, 30),
    "tool-hogs": (tool_hogs, 30), "model-mix": (model_mix, 30), "subagent-share": (subagent_share, 30),
    "weekly-summary": (weekly_summary, None),
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    fn, default = COMMANDS[argv[0]]
    arg = argv[1] if len(argv) > 1 else None
    if argv[0] == "task-estimate" and arg is None:
        print("usage: nd.py usage task-estimate <words>")
        return 2
    if default is None:
        rows = fn(arg) if arg is not None else fn()
    else:
        rows = fn(type(default)(arg) if arg is not None else default)
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
