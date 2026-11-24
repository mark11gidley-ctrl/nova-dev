"""Savings report: writes one HTML file with your tokens, context, money, plan limit, and what the guards saved.

Usage: python -I scripts/report.py [output.html]   (default: <state folder>/report.html)

Measured from your Claude Code transcripts and the guard log. Money and the plan limit only appear
when you set prices and a limit in config.json (see skills/nova-dev-settings); until then they say "not set".
Nothing is sent anywhere; the file is local and has no external links.
"""
import glob
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, HERE)
import savings  # noqa: E402
import settings  # noqa: E402
from ledger import session_totals  # noqa: E402
from state import state_dir  # noqa: E402
from stats import collect, projects_dir  # noqa: E402

PRICES = ("price_input", "price_output", "price_cache_read", "price_cache_write")


def fmt(n):
    return f"{int(n):,}"


def total_tokens(t):
    return t["input"] + t["output"] + t["cache_read"] + t["cache_create"]


def money(t, prices):
    """Dollars for the totals at the configured prices. None when no price is set."""
    if not any(prices.values()):
        return None
    return (t["input"] * prices["price_input"] + t["output"] * prices["price_output"]
            + t["cache_read"] * prices["price_cache_read"] + t["cache_create"] * prices["price_cache_write"]) / 1_000_000


def latest_context():
    files = glob.glob(os.path.join(projects_dir(), "**", "*.jsonl"), recursive=True)
    if not files:
        return None
    newest = max(files, key=os.path.getmtime)
    return session_totals(newest).get("context_tokens", 0)


def build(now=None):
    now = now or datetime.now(timezone.utc)
    prices = {k: float(settings.get(k)) for k in PRICES}
    window7 = collect(projects_dir(), 7, now)
    window30 = collect(projects_dir(), 30, now)
    limit = int(settings.get("plan_limit_tokens") or 0)
    context = latest_context()
    window = int(settings.get("window"))
    guard = savings.load()
    read = guard.get("read", {"count": 0, "bytes": 0})
    read_tokens = read["bytes"] // 4  # about 4 characters per token; an estimate, labelled as one
    cache_saved = None
    if prices["price_input"] and prices["price_cache_read"]:
        cache_saved = window30["cache_read"] * (prices["price_input"] - prices["price_cache_read"]) / 1_000_000

    rows = []

    def card(label, value, note=""):
        rows.append(f'<div class="card"><div class="label">{html.escape(label)}</div>'
                    f'<div class="value">{html.escape(str(value))}</div>'
                    f'<div class="note">{html.escape(note)}</div></div>')

    card("Tokens, last 7 days", fmt(total_tokens(window7)), f"{window7['sessions']} session(s), {window7['turns']} turn(s)")
    card("Tokens, last 30 days", fmt(total_tokens(window30)), f"{window30['sessions']} session(s), {window30['turns']} turn(s)")
    prompt_side = window30["input"] + window30["cache_read"] + window30["cache_create"]
    hit = window30["cache_read"] / prompt_side * 100 if prompt_side else 0
    card("Cache hit rate, 30 days", f"{hit:.1f}%", "share of prompt tokens served from cache")
    m7, m30 = money(window7, prices), money(window30, prices)
    card("Money, last 7 days", "not set" if m7 is None else f"${m7:,.2f}",
         "set price_input, price_output, price_cache_read, price_cache_write in config.json" if m7 is None else "at your configured prices")
    card("Money, last 30 days", "not set" if m30 is None else f"${m30:,.2f}",
         "" if m30 is not None else "same prices as above")
    if limit:
        used = total_tokens(window7)
        card("Plan limit, last 7 days", f"{used / limit * 100:.1f}% used",
             f"{fmt(used)} of {fmt(limit)} tokens")
    else:
        card("Plan limit", "not set", "set plan_limit_tokens in config.json (your limit over 7 days)")
    if context is None:
        card("Current context", "no session yet", "")
    else:
        card("Current context", f"{context / window * 100:.1f}%", f"{fmt(context)} of {fmt(window)} tokens (latest session)")
    card("Blocked repeat reads", fmt(read["count"]), f"about {fmt(read_tokens)} tokens kept out of context (estimate)")
    card("Blocked repeat commands", fmt(guard.get("bash", {"count": 0})["count"]), "identical read-only commands within 30 s")
    if cache_saved is not None:
        card("Saved by the prompt cache, 30 days", f"${cache_saved:,.2f}", "cache reads billed at the cache price instead of the input price")

    generated = now.strftime("%Y-%m-%d %H:%M UTC")
    return HTML.format(cards="\n".join(rows), generated=html.escape(generated))


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>nova-dev savings</title>
<style>
:root{{--bg:#f7f7f8;--fg:#111;--mut:#666;--card:#fff;--line:#e3e3e8;--accent:#0f766e}}
@media (prefers-color-scheme: dark){{:root:not([data-theme=light]){{--bg:#0f1115;--fg:#eee;--mut:#9aa0a6;--card:#171a21;--line:#2a2f3a;--accent:#5eead4}}}}
:root[data-theme=dark]{{--bg:#0f1115;--fg:#eee;--mut:#9aa0a6;--card:#171a21;--line:#2a2f3a;--accent:#5eead4}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:960px;margin:0 auto;padding:24px 16px}}
h1{{font-size:1.6rem;margin:0 0 4px}} .sub{{color:var(--mut);margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
.label{{color:var(--mut);font-size:.85rem}} .value{{font-size:1.5rem;font-weight:650;color:var(--accent);margin:4px 0}}
.note{{color:var(--mut);font-size:.8rem}}
footer{{margin-top:24px;color:var(--mut);font-size:.8rem}}
</style></head>
<body><main>
<h1>nova-dev savings</h1>
<div class="sub">Measured from your own Claude Code transcripts. Generated {generated}.</div>
<div class="grid">
{cards}
</div>
<footer>Money and the plan limit depend on the values you set in config.json. Nothing here was sent anywhere.</footer>
</main></body></html>
"""


SUMMARY_TTL = 300  # seconds: the transcript scan is too slow to repeat on every bar refresh


def summary_data(now=None):
    """The bar's numbers as a dict, cached for SUMMARY_TTL seconds in summary.json."""
    import time
    path = os.path.join(state_dir(), "summary.json")
    now_ts = time.time() if now is None else now
    try:
        if now_ts - os.path.getmtime(path) < SUMMARY_TTL:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    except (OSError, ValueError):
        pass
    now_dt = datetime.fromtimestamp(now_ts, timezone.utc)
    t7 = collect(projects_dir(), 7, now_dt)
    limit = int(settings.get("plan_limit_tokens") or 0)
    context = latest_context()
    window = int(settings.get("window"))
    read = savings.load().get("read", {"count": 0, "bytes": 0})
    data = {
        "tokens7": total_tokens(t7),
        "limit_pct": (total_tokens(t7) / limit * 100) if limit else None,
        "context_pct": (context / window * 100) if context is not None else None,
        "saved_reads": int(read["count"]),
        "saved_tokens": int(read["bytes"]) // 4,
        # what those tokens would have cost at your input price; None until a price is set
        "saved_cost": ((int(read["bytes"]) // 4) * float(settings.get("price_input")) / 1_000_000)
        if float(settings.get("price_input")) else None,
    }
    os.makedirs(state_dir(), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data


def summary_line(now=None):
    """The same numbers as one text line, for places that cannot draw chips."""
    d = summary_data(now)
    parts = [f"7d {fmt(d['tokens7'])} tok"]
    if d["limit_pct"] is not None:
        parts.append(f"limit {d['limit_pct']:.0f}%")
    if d["context_pct"] is not None:
        parts.append(f"ctx {d['context_pct']:.0f}%")
    parts.append(f"saved {fmt(d['saved_reads'])} reads (~{fmt(d['saved_tokens'])} tok)")
    return " | ".join(parts)


def transcript_path(cwd, session_id):
    """Claude Code keeps a session at projects/<folder>/<session>.jsonl, where the folder is the working path
    with ':', '\\' and '/' turned into '-'. Falls back to a search when the folder name differs."""
    if not session_id:
        return None
    base = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects")
    direct = os.path.join(base, re.sub(r"[:\\/]", "-", cwd or ""), f"{session_id}.jsonl")
    if os.path.isfile(direct):
        return direct
    hits = glob.glob(os.path.join(base, "*", f"{session_id}.jsonl"))
    return hits[0] if hits else None


def session_metrics(path):
    """Tokens, turns, context, and agent time for one session. Agent time is measured from the transcript:
    for each prompt you sent, the time until the last reply before your next prompt."""
    from usage import read_usage
    usage, _ = read_usage(path)
    tuples = [t for _ts, t in usage.values()]
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
    for i, o, r, c in tuples:
        totals["input"] += i
        totals["output"] += o
        totals["cache_read"] += r
        totals["cache_create"] += c
    last = list(usage.values())[-1][1] if usage else (0, 0, 0, 0)
    agent_ms = 0
    start = last_reply = None
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            ts = _parse(rec.get("timestamp"))
            if ts is None:
                continue
            if rec.get("type") == "user":
                content = (rec.get("message") or {}).get("content", "")
                is_prompt = isinstance(content, str) or (
                    isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "text" for c in content))
                if is_prompt:
                    if start is not None and last_reply is not None:
                        agent_ms += int((last_reply - start).total_seconds() * 1000)
                    start, last_reply = ts, None
            elif rec.get("type") == "assistant" and start is not None:
                last_reply = ts
    if start is not None and last_reply is not None:
        agent_ms += int((last_reply - start).total_seconds() * 1000)
    return dict(totals, turns=len(tuples), context=last[0] + last[2] + last[3], agent_ms=agent_ms)


def session_metrics_cached(path):
    """session_metrics, reused until the transcript's size or modification time changes."""
    import hashlib
    st = os.stat(path)
    digest = hashlib.sha256(os.path.abspath(path).encode("utf-8")).hexdigest()[:24]
    cache = os.path.join(state_dir(), "cache", f"session-{digest}.json")
    try:
        with open(cache, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("size") == st.st_size and data.get("mtime") == st.st_mtime_ns:
            return data["metrics"]
    except (OSError, ValueError, KeyError):
        pass
    metrics = session_metrics(path)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as fh:
        json.dump({"size": st.st_size, "mtime": st.st_mtime_ns, "metrics": metrics}, fh)
    return metrics


def _parse(text):
    try:
        return datetime.fromisoformat((text or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def clock(ms):
    s = int(ms // 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {sec:02d}s"


def session_page(cwd, session_id, cost=None, tests=None):
    """A pop-out page with everything about the current session. Local, no external links."""
    path = transcript_path(cwd, session_id)
    if not path:
        raise SystemExit("no transcript found for this session yet")
    m = session_metrics_cached(path)
    window = int(settings.get("window"))
    cards = []

    def card(label, value, note=""):
        cards.append(f'<div class="card"><div class="label">{html.escape(label)}</div>'
                     f'<div class="value">{html.escape(str(value))}</div>'
                     f'<div class="note">{html.escape(note)}</div></div>')

    card("Session cost", "not reported" if cost is None else f"${float(cost):,.2f}",
         "the cost Claude Code reports for this session" if cost is not None else "shown in the bar when Claude Code reports it")
    card("Agent time", clock(m["agent_ms"]), "time from your prompts to the last reply before the next one")
    card("Turns", fmt(m["turns"]), "assistant replies in this session")
    card("Input tokens", fmt(m["input"]), "fresh input")
    card("Output tokens", fmt(m["output"]), "what the model wrote")
    card("Cache read", fmt(m["cache_read"]), "input served from the prompt cache")
    card("Cache written", fmt(m["cache_create"]), "input stored in the prompt cache")
    card("Context now", f"{m['context'] / window * 100:.1f}%", f"{fmt(m['context'])} of {fmt(window)} tokens")
    if tests:
        card("Tests", f"{tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed", "from the last test run")
    read = savings.load().get("read", {"count": 0, "bytes": 0})
    avoided = int(read["bytes"]) // 4
    price = float(settings.get("price_input"))
    card("Repeat reads blocked", fmt(read["count"]), "all time")
    card("Tokens you would have used", f"~{fmt(avoided)}", "repeat file reads the guard kept out of context (estimate)")
    card("What those would have cost", f"${avoided * price / 1_000_000:,.2f}" if price else "not set",
         "at your input price" if price else "set price_input in config.json")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = HTML.format(cards="\n".join(cards), generated=html.escape(generated))
    page = page.replace("nova-dev savings", "nova-dev session").replace("Measured from your own Claude Code transcripts.",
                                                                       "This session, from its transcript.")
    out = os.path.join(state_dir(), "session.html")
    os.makedirs(state_dir(), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    return out


def main(argv):
    if argv and argv[0] == "--session":
        # --session <cwd> <session_id> [cost] [passed failed]
        cost = argv[3] if len(argv) > 3 and argv[3] not in ("", "None") else None
        tests = None
        if len(argv) > 5 and argv[4].isdigit() and argv[5].isdigit():
            tests = {"passed": int(argv[4]), "failed": int(argv[5])}
        print(session_page(argv[1], argv[2], cost, tests))
        return 0
    out = argv[0] if argv else os.path.join(state_dir(), "report.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build())
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
