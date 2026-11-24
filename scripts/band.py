"""Band commands.

  python -I scripts/band.py import            add past Claude Code sessions to the ledger
  python -I scripts/band.py last              print the most recent task as Markdown
  python -I scripts/band.py board             write an HTML board and print its path
  python -I scripts/band.py show [days]       table of tasks in the last N days (default 30)
"""
import datetime as dt
import html
import os
import sys
from datetime import timedelta

import glob  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, HERE)
from ledger import band_dir, read_all, state_dir, upsert_row, make_row  # noqa: E402
import stats  # noqa: E402


def import_past(base=None):
    count = 0
    root = stats.projects_dir()
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        project = os.path.basename(os.path.dirname(path))
        row = make_row(os.path.splitext(os.path.basename(path))[0], path, project)
        upsert_row(row, base)
        count += 1
    return count


def _safe_cell(value):
    """Spreadsheets run cells that start with = + - @ as formulas; neutralize them."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def as_markdown(row):
    return "\n".join([
        f"**Task:** {row.get('task') or '(no prompt)'}",
        f"- Project: {row['project']}",
        f"- Turns: {row['turns']}",
        f"- Tokens: input {int(row['input']):,}, output {int(row['output']):,}, "
        f"cache read {int(row['cache_read']):,}, cache created {int(row['cache_create']):,}",
        f"- Latest context: {int(row['context_tokens']):,} tokens",
        f"- Recorded: {row['timestamp']}",
    ])


def board_html(rows):
    def num(v):
        return int(float(v or 0))

    by_project = {}
    by_day = {}
    for r in rows:
        p = by_project.setdefault(r["project"], {"sessions": 0, "tokens": 0})
        p["sessions"] += 1
        total = sum(num(r[k]) for k in ("input", "output", "cache_read", "cache_create"))
        p["tokens"] += total
        day = (r.get("timestamp") or "")[:10] or "unknown"
        by_day[day] = by_day.get(day, 0) + total
    recent = sorted(rows, key=lambda r: r.get("timestamp", ""), reverse=True)[:50]
    maxday = max(by_day.values()) if by_day else 1

    proj_rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{v['sessions']}</td><td>{v['tokens']:,}</td></tr>"
        for k, v in sorted(by_project.items(), key=lambda kv: kv[1]["tokens"], reverse=True))
    day_rows = "".join(
        f"<tr><td>{html.escape(d)}</td><td>{t:,}</td>"
        f"<td><div class='bar' style='width:{int(100 * t / maxday)}%'></div></td></tr>"
        for d, t in sorted(by_day.items()))
    task_rows = "".join(
        f"<tr><td>{html.escape(r.get('timestamp', ''))}</td><td>{html.escape(r['project'])}</td>"
        f"<td>{html.escape(r.get('task', ''))}</td><td>{num(r.get('turns'))}</td>"
        f"<td>{sum(num(r[k]) for k in ('input', 'output', 'cache_read', 'cache_create')):,}</td></tr>"
        for r in recent)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>nova-dev board</title>
<style>
:root{{--bg:#fff;--fg:#111;--mut:#666;--bar:#111}}
@media (prefers-color-scheme: dark){{:root:not([data-theme=light]){{--bg:#111;--fg:#eee;--mut:#999;--bar:#eee}}}}
body{{background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;margin:16px}}
table{{border-collapse:collapse;width:100%;margin-bottom:24px}}
td,th{{border-bottom:1px solid var(--mut);padding:6px;text-align:left}}
.bar{{background:var(--bar);height:10px}}
</style></head><body>
<h1>nova-dev board</h1>
<h2>Tokens per day</h2><table><tr><th>Day</th><th>Tokens</th><th></th></tr>{day_rows}</table>
<h2>Projects</h2><table><tr><th>Project</th><th>Sessions</th><th>Tokens</th></tr>{proj_rows}</table>
<h2>Latest tasks</h2><table><tr><th>When</th><th>Project</th><th>Task</th><th>Turns</th><th>Tokens</th></tr>{task_rows}</table>
</body></html>"""


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "import":
        print(f"Imported {import_past()} session(s) into {band_dir()}")
    elif cmd == "last":
        rows = sorted(read_all(), key=lambda r: r.get("timestamp", ""))
        print(as_markdown(rows[-1]) if rows else "No tasks yet.")
    elif cmd == "board":
        out = os.path.join(state_dir(), "board.html")
        os.makedirs(state_dir(), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(board_html(read_all()))
        print(out)
    elif cmd == "export":
        import csv as _csv
        import io
        import json as _json
        fmt = sys.argv[2] if len(sys.argv) > 2 else "json"
        rows = read_all()
        if fmt == "json":
            print(_json.dumps(rows, indent=2))
        elif fmt == "csv":
            buf = io.StringIO()
            if rows:
                w = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows([{k: _safe_cell(v) for k, v in r.items()} for r in rows])
            print(buf.getvalue(), end="")
        else:
            print("export format must be json or csv")
            sys.exit(2)
    elif cmd == "show":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        cutoff = (dt.datetime.now(dt.timezone.utc) - timedelta(days=days)).isoformat()
        rows = [r for r in read_all() if r.get("timestamp", "") >= cutoff[:19]]
        print(f"{len(rows)} task(s) in the last {days} days")
        for r in sorted(rows, key=lambda r: r.get("timestamp", ""), reverse=True):
            print(f"{r['timestamp']}  {r['project']:<24} turns={r['turns']:<5} {r.get('task', '')}")
    else:
        print(__doc__)
    sys.exit(0)
