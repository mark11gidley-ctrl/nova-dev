"""Savings log: how often the guards blocked repeat work, and how many bytes of file content they kept
out of context. Written by the hooks, read by the report. Counts are exact; byte totals are file sizes."""
import json
import os

from state import state_dir


def _path():
    return os.path.join(state_dir(), "savings.json")


def load():
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record(kind, bytes_avoided=0):
    """Add one blocked action of this kind. Never raises for a bad file: a missing log starts empty."""
    data = load()
    entry = data.get(kind, {"count": 0, "bytes": 0})
    entry["count"] = int(entry.get("count", 0)) + 1
    entry["bytes"] = int(entry.get("bytes", 0)) + int(bytes_avoided)
    data[kind] = entry
    os.makedirs(state_dir(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, _path())
