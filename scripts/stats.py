"""Measured token use from your own Claude Code transcripts (no estimates).

Usage: python -I scripts/stats.py [days] [--top N] [--by-project]   (days default 30)
Reads <CLAUDE_CONFIG_DIR or ~/.claude>/projects/**/*.jsonl with the shared rules in hooks/usage.py.
"""
import glob
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
from usage import read_usage, sum_totals  # noqa: E402


def projects_dir():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def parse_ts(text):
    try:
        return datetime.fromisoformat((text or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def collect(base, days, now, per_session=None):
    """Totals for the window. per_session (optional) receives tokens per transcript file."""
    cutoff = now - timedelta(days=days)
    per_session = {} if per_session is None else per_session
    tuples = []
    sessions = 0
    for path in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
        if os.path.getmtime(path) < cutoff.timestamp():  # untouched since before the window
            continue
        usage, _ = read_usage(path)
        kept = [tup for ts, tup in usage.values() if (parse_ts(ts) or cutoff) >= cutoff]
        if not kept:
            continue
        sessions += 1
        tuples.extend(kept)
        per_session[os.path.splitext(os.path.basename(path))[0]] = sum(sum(t) for t in kept)
    totals = sum_totals(tuples)
    totals["sessions"] = sessions
    return totals


def report(totals, days):
    prompt_side = totals["input"] + totals["cache_read"] + totals["cache_create"]
    hit = (totals["cache_read"] / prompt_side * 100) if prompt_side else 0.0
    lines = [
        f"Last {days} days: {totals['sessions']} session(s), {totals['turns']} assistant turn(s)",
        f"  input (uncached)   {totals['input']:>14,}",
        f"  cache read         {totals['cache_read']:>14,}",
        f"  cache created      {totals['cache_create']:>14,}",
        f"  output             {totals['output']:>14,}",
        f"  cache hit rate     {hit:>13.1f}%",
    ]
    return "\n".join(lines)


def top_sessions(per_session, n):
    rows = sorted(per_session.items(), key=lambda kv: kv[1], reverse=True)[:n]
    lines = [f"Top {len(rows)} session(s) by total tokens:"]
    lines += [f"  {total:>14,}  {session}" for session, total in rows]
    return "\n".join(lines)


def by_project_report(base, days, now):
    """Tokens per project folder over the window. Folder names come from Claude Code's project paths."""
    cutoff = now - timedelta(days=days)
    totals = {}
    for path in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
        if os.path.getmtime(path) < cutoff.timestamp():
            continue
        project = os.path.basename(os.path.dirname(path))
        usage, _ = read_usage(path)
        for ts, tup in usage.values():
            if (parse_ts(ts) or cutoff) >= cutoff:
                totals[project] = totals.get(project, 0) + sum(tup)
    rows = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:20]
    return "Tokens by project:\n" + "\n".join(f"  {t:>14,}  {p}" for p, t in rows)


def _main():
    args = sys.argv[1:]
    top = 0
    if "--top" in args:
        i = args.index("--top")
        top = int(args[i + 1])
        del args[i:i + 2]
    by_project_flag = "--by-project" in args
    args = [a for a in args if a != "--by-project"]
    days = int(args[0]) if args else 30
    now = datetime.now(timezone.utc)
    per_session = {}
    totals = collect(projects_dir(), days, now, per_session)
    print(report(totals, days))
    if top:
        print(top_sessions(per_session, top))
    if by_project_flag:
        print(by_project_report(projects_dir(), days, now))
    sys.exit(0)


if __name__ == "__main__":
    _main()
