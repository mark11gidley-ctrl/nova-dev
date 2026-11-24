"""More game tools. Used through: nd.py game <name> [args]

Gameplay code
  frame-loop-check [root]         while-true loops in game code with no frame, sleep or clock call
  input-map-check <keys.json> [root]   keys the code reads that the keybinding file does not define
  gameplay-numbers [root]         numbers typed straight into player, enemy or combat code

Levels and progression
  level-stats <level.json>        rooms, connections and dead ends
  wave-plan <waves.json>          enemies per wave and how fast the count grows
  progression-check <tree.json>   unlock trees: unknown prerequisites and cycles
  stat-sanity <items.json>        stats outside sensible bounds (negative health, zero cost)
  quest-check <quests.json>       quests that name a missing prerequisite or next step
  dialogue-check <dialogue.json>  dialogue nodes that point nowhere, and dead ends

Assets
  texture-budget [root]           video memory estimate for PNG files (width x height x 4 bytes)
  audio-length [root]             length of WAV files, from their headers
  asset-names [root]              asset names that engines often break on (spaces, non-ASCII)
  duplicate-assets [root]         files with identical content

Build, release and telemetry
  build-budget <max_mb> [root]    total size of the build folder against a budget
  release-notes [since_tag]       commit messages since a tag, grouped by feat/fix/other
  session-stats <playtest.csv>    minutes and issues per hour, per build
  crash-group <log> [root]        crash tracebacks grouped by exception type

Engine code
  unity-class-names [root]        C# classes whose name does not match the file (Unity needs them to match)
  godot-signals [root]            GDScript connect() calls to methods the same file does not define

Read-only, except nothing: every tool here only reads.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import wave
from collections import Counter, defaultdict

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "Library", "Temp", "obj"}


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield os.path.join(dirpath, f)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---- gameplay code ----

def frame_loop_check(root):
    rows = []
    for path in walk(root):
        if not path.endswith((".py", ".js", ".ts", ".gd", ".cs")):
            continue
        lines = read(path).splitlines()
        for i, line in enumerate(lines):
            if re.search(r"while\s*(True|true|1)\s*:|while\s*\(\s*true\s*\)", line):
                body = "\n".join(lines[i:i + 25])
                if not re.search(r"sleep|clock|tick|frame|delta|time|requestAnimationFrame|yield|await|wait", body, re.I):
                    rows.append(f"{os.path.relpath(path, root)}:{i + 1}  loop with no frame, sleep or clock call")
    return rows or ["every game loop waits for a frame or clock"]


def input_map_check(keys_path, root):
    defined = set(load(keys_path))
    used = Counter()
    for path in walk(root):
        if path.endswith((".py", ".js", ".ts", ".gd", ".cs")):
            for k in re.findall(r"is_action_pressed\(\s*[\"']([\w]+)[\"']|GetKey\(\s*KeyCode\.(\w+)|key_pressed\(\s*[\"']([\w]+)[\"']|\bkey\s*==\s*[\"']([\w]+)[\"']", read(path)):
                name = next(x for x in k if x)
                used[name] += 1
    rows = [f"used in code but not defined: {name} ({n}x)" for name, n in used.items() if name not in defined]
    return rows or ["every key the code reads is defined"]


GAMEPLAY = re.compile(r"player|enemy|combat|damage|health|weapon|spawn|boss", re.I)
NUM = re.compile(r"(?<![\w.])(\d+\.?\d*)(?![\w.])")


def gameplay_numbers(root):
    rows = []
    for path in walk(root):
        if not path.endswith((".py", ".js", ".ts", ".gd", ".cs")) or not GAMEPLAY.search(os.path.basename(path)):
            continue
        for i, line in enumerate(read(path).splitlines(), 1):
            code = line.split("#")[0].split("//")[0]
            if "=" in code and not re.match(r"\s*[A-Z_]+\s*=", code):
                nums = [n for n in NUM.findall(code) if n not in ("0", "1", "2", "0.0", "1.0")]
                if nums:
                    rows.append(f"{os.path.relpath(path, root)}:{i}  {', '.join(nums)}")
    return rows or ["no bare numbers in gameplay files"]


# ---- levels and progression ----

def _graph_problems(nodes, edges_of, label):
    rows = []
    for n in nodes:
        for m in edges_of(n):
            if m not in nodes:
                rows.append(f"{label} '{n}' points to missing '{m}'")
    return rows


def level_stats(path):
    level = load(path)
    rooms = level.get("rooms", {})
    edges = sum(len(v) for v in rooms.values())
    dead = [r for r, v in rooms.items() if not v and r != level.get("exit")]
    return [f"rooms: {len(rooms)}, connections: {edges}",
            f"dead ends (not the exit): {', '.join(dead) or 'none'}"]


def wave_plan(path):
    waves = load(path)
    counts = [sum(w.get("enemies", {}).values()) if isinstance(w, dict) else 0 for w in waves]
    rows = [f"wave {i + 1}: {c} enemies" for i, c in enumerate(counts)]
    if len(counts) > 1 and counts[0] > 0:
        growth = (counts[-1] / counts[0]) ** (1 / (len(counts) - 1))
        rows.append(f"average growth per wave: x{growth:.2f}")
    return rows


def progression_check(path):
    tree = load(path)
    nodes = set(tree)
    rows = _graph_problems(nodes, lambda n: tree[n].get("requires", []), "unlock")
    state = {}

    def visit(n, stack):
        state[n] = 1
        for m in tree.get(n, {}).get("requires", []):
            if m not in nodes:
                continue
            if state.get(m) == 1:
                rows.append("cycle: " + " -> ".join(stack + [m]))
            elif m not in state:
                visit(m, stack + [m])
        state[n] = 2

    for n in nodes:
        if n not in state:
            visit(n, [n])
    return rows or ["no cycles, no missing prerequisites"]


def stat_sanity(path):
    rows = []
    for item in load(path):
        name = item.get("name", "?")
        for stat in ("health", "damage", "speed", "cost", "price"):
            v = item.get(stat)
            if v is not None and v < 0:
                rows.append(f"{name}: {stat} is negative ({v})")
        if item.get("cost") == 0 or item.get("price") == 0:
            rows.append(f"{name}: free (zero cost or price)")
        if item.get("health") == 0:
            rows.append(f"{name}: health is zero")
    return rows or ["all stats within sensible bounds"]


def quest_check(path):
    quests = load(path)
    ids = {q["id"] for q in quests if "id" in q}
    rows = []
    for q in quests:
        for need in q.get("requires", []):
            if need not in ids:
                rows.append(f"{q.get('id', '?')}: needs missing quest '{need}'")
        if q.get("next") and q["next"] not in ids:
            rows.append(f"{q.get('id', '?')}: next step '{q['next']}' is missing")
    return rows or ["every quest prerequisite exists"]


def dialogue_check(path):
    nodes = load(path)
    ids = set(nodes)
    rows = _graph_problems(ids, lambda n: [c for c in nodes[n].get("next", []) if isinstance(c, str)], "node")
    for n, body in nodes.items():
        if not body.get("next") and not body.get("end"):
            rows.append(f"dead end: node '{n}' has no next line and is not marked end")
    return rows or ["every dialogue node leads somewhere"]


# ---- assets ----

def _png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def texture_budget(root):
    rows = []
    total = 0
    for path in walk(root):
        if path.lower().endswith(".png"):
            size = _png_size(path)
            if size:
                bytes_ = size[0] * size[1] * 4
                total += bytes_
                rows.append((bytes_, f"{bytes_ / 1048576:8.2f} MB  {os.path.relpath(path, root)} ({size[0]}x{size[1]})"))
    rows.sort(reverse=True)
    return [r for _, r in rows[:15]] + [f"total uncompressed: {total / 1048576:.1f} MB across {len(rows)} PNG file(s)"]


def audio_length(root):
    rows = []
    for path in walk(root):
        if path.lower().endswith(".wav"):
            try:
                with wave.open(path, "rb") as w:
                    secs = w.getnframes() / w.getframerate()
                rows.append(f"{secs:7.2f} s  {os.path.relpath(path, root)}")
            except (wave.Error, OSError, EOFError):
                rows.append(f"unreadable WAV: {os.path.relpath(path, root)}")
    return rows or ["no WAV files found"]


def asset_names(root):
    rows = []
    for path in walk(root):
        if "/assets/" in "/" + os.path.relpath(path, root).replace(os.sep, "/"):
            name = os.path.basename(path)
            if " " in name or not name.isascii():
                rows.append(f"{os.path.relpath(path, root)}: spaces or non-ASCII characters")
    return rows or ["asset names are safe for engines"]


def duplicate_assets(root):
    by_hash = defaultdict(list)
    for path in walk(root):
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".wav", ".ogg", ".mp3")):
            with open(path, "rb") as fh:
                by_hash[hashlib.sha256(fh.read()).hexdigest()].append(os.path.relpath(path, root))
    rows = [" = ".join(sorted(v)) for v in by_hash.values() if len(v) > 1]
    return rows or ["no duplicate assets"]


# ---- build, release, telemetry ----

def build_budget(max_mb, root):
    total = sum(os.path.getsize(p) for p in walk(root))
    mb = total / 1048576
    verdict = "within budget" if mb <= max_mb else f"OVER budget by {mb - max_mb:.1f} MB"
    return [f"build: {mb:.1f} MB of {max_mb} MB ({verdict})"]


def release_notes(since=None):
    rng = f"{since}..HEAD" if since else "HEAD"
    out = subprocess.run(["git", "log", "--format=%s", rng], capture_output=True, text=True)
    if out.returncode != 0:
        return [f"git log failed: {out.stderr.strip()}"]
    groups = defaultdict(list)
    for subject in out.stdout.splitlines():
        m = re.match(r"^(feat|fix|docs|test|refactor|chore)(\(.+?\))?:\s*(.+)", subject)
        kind, text = (m.group(1), m.group(3)) if m else ("other", subject)
        groups[kind].append(text)
    names = {"feat": "Added", "fix": "Fixed", "docs": "Docs", "test": "Tests", "refactor": "Changed", "chore": "Maintenance", "other": "Other"}
    rows = []
    for kind in ("feat", "fix", "refactor", "docs", "test", "chore", "other"):
        if groups.get(kind):
            rows.append(f"## {names[kind]}")
            rows += [f"- {t}" for t in groups[kind]]
    return rows or ["no commits in range"]


def session_stats(path):
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    per = defaultdict(lambda: [0.0, 0])
    for r in rows:
        per[r["build"]][0] += float(r["minutes"] or 0)
        per[r["build"]][1] += 1
    out = []
    for build, (mins, sessions) in sorted(per.items()):
        hours = mins / 60 or 1
        out.append(f"build {build}: {sessions} session(s), {mins:.0f} min, {sessions / hours:.2f} sessions per hour")
    return out or ["no sessions logged"]


def crash_group(log_path, root):
    text = read(log_path)
    kinds = Counter(re.findall(r"^(?:[\w.]+\.)?([A-Z]\w*(?:Error|Exception))\b", text, re.M))
    kinds.update(re.findall(r"^Traceback.*?\n(?:.*\n)*?(\w+Error)", text, re.M))
    rows = [f"{n}x  {k}" for k, n in kinds.most_common()]
    return rows or ["no exception types found in the log"]


def unity_class_names(root):
    rows = []
    for path in walk(root):
        if path.endswith(".cs"):
            stem = os.path.splitext(os.path.basename(path))[0]
            classes = re.findall(r"\b(?:class|struct)\s+(\w+)", read(path))
            if classes and stem not in classes:
                rows.append(f"{os.path.relpath(path, root)}: no class named {stem} (classes: {', '.join(classes[:3])})")
    return rows or ["every C# file's class matches its file name"]


def godot_signals(root):
    rows = []
    for path in walk(root):
        if not path.endswith(".gd"):
            continue
        text = read(path)
        defined = set(re.findall(r"^func\s+(\w+)", text, re.M))
        for target in re.findall(r"\.connect\(\s*\"?\w*\"?\s*,?\s*self\.?(\w+)|\.connect\(\s*(\w+)\s*\)", text):
            name = next(x for x in target if x)
            if name not in defined and name not in ("self",):
                rows.append(f"{os.path.relpath(path, root)}: connects to '{name}' but this file does not define it")
    return rows or ["every connected signal handler is defined in its file"]


COMMANDS = {
    "frame-loop-check": (lambda a, r: frame_loop_check(a[0] if a else r)),
    "input-map-check": (lambda a, r: input_map_check(a[0], a[1] if len(a) > 1 else r)),
    "gameplay-numbers": (lambda a, r: gameplay_numbers(a[0] if a else r)),
    "level-stats": (lambda a, r: level_stats(a[0])),
    "wave-plan": (lambda a, r: wave_plan(a[0])),
    "progression-check": (lambda a, r: progression_check(a[0])),
    "stat-sanity": (lambda a, r: stat_sanity(a[0])),
    "quest-check": (lambda a, r: quest_check(a[0])),
    "dialogue-check": (lambda a, r: dialogue_check(a[0])),
    "texture-budget": (lambda a, r: texture_budget(a[0] if a else r)),
    "audio-length": (lambda a, r: audio_length(a[0] if a else r)),
    "asset-names": (lambda a, r: asset_names(a[0] if a else r)),
    "duplicate-assets": (lambda a, r: duplicate_assets(a[0] if a else r)),
    "build-budget": (lambda a, r: build_budget(float(a[0]), a[1] if len(a) > 1 else r)),
    "release-notes": (lambda a, r: release_notes(a[0] if a else None)),
    "session-stats": (lambda a, r: session_stats(a[0])),
    "crash-group": (lambda a, r: crash_group(a[0], a[1] if len(a) > 1 else r)),
    "unity-class-names": (lambda a, r: unity_class_names(a[0] if a else r)),
    "godot-signals": (lambda a, r: godot_signals(a[0] if a else r)),
}


def run(cmd, args, root=None):
    return COMMANDS[cmd](args, root or os.getcwd())


if __name__ == "__main__":
    if not sys.argv[1:] or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    for r in run(sys.argv[1], sys.argv[2:]):
        print(r)
