"""Band ledger: one row per session in ~/.config/nova-dev/band/<project>.csv, plus an
optional https webhook. Reads transcripts only; nothing leaves the machine unless a webhook URL is set.

Transcript totals are cached per file and only new bytes are parsed on later calls, so the Stop
hook stays fast on long sessions."""
import csv
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

from redact import redact_text
from state import state_dir
from usage import context_size, read_usage, sum_totals

FIELDS = ["timestamp", "project", "session", "task", "turns", "input", "output",
          "cache_read", "cache_create", "context_tokens"]


def band_dir():
    return os.path.join(state_dir(), "band")


def _safe(name):
    return re.sub(r"[^\w.-]", "_", name or "unknown") or "unknown"


def project_name(cwd):
    return os.path.basename(os.path.normpath(cwd)) if cwd else "unknown"


def _cache_path(path):
    digest = hashlib.sha256(os.path.abspath(path).encode("utf-8")).hexdigest()[:24]
    return os.path.join(state_dir(), "cache", digest + ".json")


def _load_cache(path, size):
    try:
        with open(_cache_path(path), encoding="utf-8") as fh:
            cache = json.load(fh)
    except (OSError, ValueError):
        return {"offset": 0, "usage": {}}
    if cache.get("offset", 0) > size:  # transcript was replaced or truncated
        return {"offset": 0, "usage": {}}
    return cache


def _save_cache(path, cache):
    os.makedirs(os.path.join(state_dir(), "cache"), exist_ok=True)
    with open(_cache_path(path), "w", encoding="utf-8") as fh:
        json.dump(cache, fh)


def session_totals(path):
    """Totals for one transcript. Streamed chunks with the same message id count once (final usage wins).
    Only bytes written since the last call are parsed; complete lines only, so a partly written line waits."""
    cache = _load_cache(path, os.path.getsize(path))
    usage, offset = read_usage(path, cache["usage"], cache["offset"])
    _save_cache(path, {"offset": offset, "usage": usage})
    totals = sum_totals(tup for _ts, tup in usage.values())
    totals["context_tokens"] = context_size(list(usage.values())[-1][1]) if usage else 0
    return totals


def first_user_prompt(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") != "user":
                continue
            content = (rec.get("message") or {}).get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content
                                   if isinstance(c, dict) and c.get("type") == "text")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def make_row(session_id, transcript, cwd):
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": project_name(cwd),
        "session": session_id or os.path.basename(transcript),
        "task": redact_text(" ".join(first_user_prompt(transcript).split())[:80]),
    }
    row.update(session_totals(transcript))
    return row


def upsert_row(row, base=None):
    """Replace this session's row, or add it. Keeps one row per session."""
    folder = base or band_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, _safe(row["project"]) + ".csv")
    rows = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("session") != row["session"]]
    rows.append({k: row.get(k, "") for k in FIELDS})
    # write a temp file, then swap it in: a reader never sees half a file, and a crash never truncates it
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)
    return path


def read_all(base=None):
    folder = base or band_dir()
    rows = []
    if not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if name.endswith(".csv"):
            with open(os.path.join(folder, name), newline="", encoding="utf-8") as fh:
                rows.extend(csv.DictReader(fh))
    return rows


def build_payload(row, send_names):
    data = {k: v for k, v in row.items() if k != "task"}
    if send_names:
        data["task"] = row.get("task", "")
    return data


def send_webhook(payload, url, token="", opener=urllib.request.urlopen, retries=2):
    """POST the payload. https only. Retries transient network errors; raises after the last try."""
    if not url:
        return False
    if not url.startswith("https://"):
        raise ValueError("webhook URL must start with https://")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    last = None
    for _ in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with opener(req, timeout=5) as resp:
                if resp.status < 300:
                    return True
                last = OSError(f"webhook returned HTTP {resp.status}")
        except OSError as exc:
            last = exc
    raise last
