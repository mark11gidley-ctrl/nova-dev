"""Live Nova Dev page: keep it open in a browser tab next to any chat app (ChatGPT, Codex, Claude).

Usage: python -I scripts/live.py [folder] [seconds]     (folder defaults to here; 10 seconds between updates)
Writes <state folder>/live.html and rewrites it every few seconds. Stop with Ctrl+C.
The page refreshes itself, so no app needs to support a status line for it to show up.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report  # noqa: E402
from state import state_dir  # noqa: E402


def write_once(cwd, interval):
    session = report.newest_session(cwd)
    out = os.path.join(state_dir(), "live.html")
    os.makedirs(state_dir(), exist_ok=True)
    if session:
        page_path = report.session_page(cwd, session, refresh=interval)
        os.replace(page_path, out)
    else:
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f'<!doctype html><meta http-equiv="refresh" content="{interval}"><title>nova-dev live</title>'
                     "<p>No Claude Code session found for this folder yet.</p>")
    return out


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, ".."))
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    path = write_once(folder, seconds)
    print(f"live page: {path}  (open it in a browser; updates every {seconds} s; Ctrl+C to stop)", flush=True)
    try:
        while True:
            time.sleep(seconds)
            write_once(folder, seconds)
    except KeyboardInterrupt:
        sys.exit(0)
