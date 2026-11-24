"""Savings report: writes one HTML file with your tokens, context, money, plan limit, and what the guards saved.

Usage: python -I scripts/report.py [output.html]   (default: <state folder>/report.html)

Measured from your Claude Code transcripts and the guard log. Money and the plan limit only appear
when you set prices and a limit in config.json (see skills/nova-dev-settings); until then they say "not set".
Nothing is sent anywhere; the file is local and has no external links.
"""
import glob
import html
import os
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


def summary_line(now=None):
    """One short line for the status bar, cached for SUMMARY_TTL seconds."""
    import time
    path = os.path.join(state_dir(), "summary.txt")
    now_ts = time.time() if now is None else now
    try:
        if now_ts - os.path.getmtime(path) < SUMMARY_TTL:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
    except OSError:
        pass
    now_dt = datetime.fromtimestamp(now_ts, timezone.utc)
    prices = {k: float(settings.get(k)) for k in PRICES}
    t7 = collect(projects_dir(), 7, now_dt)
    m7 = money(t7, prices)
    limit = int(settings.get("plan_limit_tokens") or 0)
    context = latest_context()
    window = int(settings.get("window"))
    read = savings.load().get("read", {"count": 0, "bytes": 0})
    parts = [f"7d {fmt(total_tokens(t7))} tok"]
    parts.append("money not set" if m7 is None else f"${m7:,.2f}")
    if limit:
        parts.append(f"limit {total_tokens(t7) / limit * 100:.0f}%")
    if context is not None:
        parts.append(f"ctx {context / window * 100:.0f}%")
    parts.append(f"saved {fmt(read['count'])} reads (~{fmt(read['bytes'] // 4)} tok)")
    line = " | ".join(parts)
    os.makedirs(state_dir(), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(line)
    return line


def main(argv):
    out = argv[0] if argv else os.path.join(state_dir(), "report.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build())
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
