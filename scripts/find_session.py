"""Find past sessions by what you asked: search your own prompts across all transcripts.

Usage: python -I scripts/find_session.py <words> [limit]   (default limit 15, newest first)
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stats  # noqa: E402


def prompt_text(rec):
    content = (rec.get("message") or {}).get("content", "")
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return content if isinstance(content, str) else ""


def find(base, needle, limit=15):
    needle = needle.lower()
    hits = []
    for path in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
        session = os.path.splitext(os.path.basename(path))[0]
        project = os.path.basename(os.path.dirname(path))
        try:
            fh = open(path, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "user":
                    continue
                text = prompt_text(rec)
                at = text.lower().find(needle)
                if at >= 0:
                    start = max(0, at - 60)
                    snippet = " ".join(text[start:at + 100].split())
                    hits.append((rec.get("timestamp", ""), session, project, snippet))
    hits.sort(reverse=True)
    return hits[:limit]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    rows = find(stats.projects_dir(), sys.argv[1], limit)
    if not rows:
        print("no matching prompts")
    for ts, session, project, snippet in rows:
        print(f"{ts[:16]}  {session}  [{project}]\n    ...{snippet}...")
    sys.exit(0)
