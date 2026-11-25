"""Nova Dev window: the bar as a small desktop window, reading the plugin's own data.

Usage: python -I scripts/bar_window.py [folder]     (folder defaults to the nova-dev folder)

It is an ordinary window. It goes on top of other windows (ChatGPT, Codex, anything) only when you press
"Pin on top", and "Pin on top" can be turned off again. Closing it stops it. Refreshes every 5 seconds.
Uses only the standard library (tkinter), and reads the same numbers as the bar in Claude Code.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
REFRESH_MS = 5000


def clock(ms):
    s = int((ms or 0) // 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {sec:02d}s"


def tokens(n):
    n = float(n or 0)
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else f"{int(n)}"


def meter(pct, width=12):
    filled = max(0, min(width, round((pct or 0) / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def lines_for(data):
    """The window's text lines from the bar's data. Missing values are left out, never an error."""
    out = []
    level = data.get("level") or "unset"
    tests = data.get("tests_counts")
    head = f"● {level.upper()}   {data.get('project', '')}"
    if tests:
        head += f"   ✓ {tests['passed']} passed" + (f"   ✗ {tests['failed']} failing" if tests.get("failed") else "")
    out.append(("head", head))
    s = data.get("session")
    if s:
        out.append(("session", f"⏱ {clock(s.get('agent_ms'))}   ↑ {tokens(s['input'] + s['cache_read'] + s['cache_create'])} in"
                               f"   ↓ {tokens(s['output'])} out   {s.get('turns', 0)} turns"))
        pct = s["context"] / 2e5 * 100 if s.get("context") is not None else None
        if pct is not None:
            out.append(("context", f"ctx {meter(pct)} {pct:.0f}%"))
    sm = data.get("summary")
    if sm:
        if sm.get("limit_pct") is not None:
            out.append(("limit", f"limit {meter(sm['limit_pct'])} {sm['limit_pct']:.0f}%"))
        out.append(("week", f"7d {tokens(sm.get('tokens7'))} tokens"))
        saved = f"saved ~{tokens(sm.get('saved_tokens'))} tokens"
        if sm.get("saved_cost") is not None:
            saved += f"   ${sm['saved_cost']:.2f}"
        out.append(("saved", saved + f"   {sm.get('saved_reads', 0)} repeats blocked"))
    return out


def fetch(folder):
    from statusline import band_data
    from report import newest_session
    return band_data(folder, newest_session(folder))


def main(argv):
    import tkinter as tk
    folder = os.path.abspath(argv[0]) if argv else os.path.abspath(os.path.join(HERE, ".."))
    root = tk.Tk()
    root.title("Nova Dev")
    root.configure(bg="#111827")
    root.geometry("560x210+40+40")
    pinned = tk.BooleanVar(value=False)
    top = tk.Frame(root, bg="#111827")
    top.pack(fill="x", padx=12, pady=(10, 0))
    tk.Checkbutton(top, text="Pin on top", variable=pinned, bg="#111827", fg="#e5e7eb", selectcolor="#1f2937",
                   activebackground="#111827", activeforeground="#e5e7eb",
                   command=lambda: root.attributes("-topmost", pinned.get())).pack(side="left")
    tk.Button(top, text="Close", command=root.destroy, bg="#374151", fg="#e5e7eb", relief="flat").pack(side="right")
    body = tk.Label(root, text="", justify="left", anchor="w", bg="#111827", fg="#e5e7eb", font=("Segoe UI", 11))
    body.pack(fill="both", expand=True, padx=12, pady=8)
    updated = tk.Label(root, text="", bg="#111827", fg="#6b7280", font=("Segoe UI", 8))
    updated.pack(anchor="w", padx=12, pady=(0, 6))

    def refresh():
        try:
            rows = lines_for(fetch(folder))
            body.config(text="\n".join(text for _kind, text in rows))
            updated.config(text=f"updated {time.strftime('%H:%M:%S')}")
        except Exception as exc:  # the window stays up and says what went wrong
            body.config(text=f"could not read nova-dev data: {exc}")
        root.after(REFRESH_MS, refresh)

    refresh()
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
