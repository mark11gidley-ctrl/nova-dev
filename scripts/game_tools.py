"""Game design and data tools. Usage: nd.py game <name> [args]

Works with any engine: these read plain JSON/CSV and game source text.

  balance-curve <base> <growth> <levels>   XP or stat values per level; flags jumps over 2x
  dps <damage> <interval_s> [crit_chance] [crit_mult] [armor_pct]
  xp-table <base> <growth> <max_level>     level thresholds as JSON
  drop-check <weights.json>                drop table totals; flags if not 100 percent
  loot-sim <weights.json> <trials> [seed]  simulated drops (seeded), compared with the weights
  economy-check <items.json> [lo] [hi]     price-to-value ratios outside the band
  level-check <level.json>                 rooms unreachable, or behind locks no key opens
  asset-audit [root]                       assets referenced in code/data but missing on disk
  asset-size [root] [n]                    largest asset files
  spritesheet <png> <frame_w> <frame_h>    frame count from the PNG header
  localization [root]                      keys used in code but missing from locale JSON
  rng-seed [root]                          random calls in a file with no seed call nearby
  save-format [root]                       save files without a version field
  playtest-log <file> <build> <minutes> <severity> <note>   append one session row
  playtest-summary <file>                  sessions, minutes and issues by severity
  design-doc <title>                       a game design document skeleton
  golden-diff <actual.json> <golden.json>  keys whose values differ between two JSON files
"""
import csv
import datetime as dt
import json
import math
import os
import random
import re
import struct
import sys
from collections import Counter

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "Library", "Temp"}
ASSET_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".wav", ".ogg", ".mp3", ".ttf", ".otf", ".json", ".tscn", ".tres")


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield os.path.join(dirpath, f)


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


# ---- balance and economy ----

def balance_curve(base, growth, levels):
    rows = []
    prev = None
    for i in range(1, levels + 1):
        value = round(base * growth ** (i - 1))
        flag = "  <- jump over 2x" if prev and value > prev * 2 else ""
        rows.append(f"level {i:>3}: {value:>10,}{flag}")
        prev = value
    return rows


def dps(damage, interval, crit_chance=0.0, crit_mult=2.0, armor_pct=0.0):
    per_hit = damage * (1 - armor_pct / 100) * (1 + crit_chance * (crit_mult - 1))
    return [f"{per_hit / interval:.2f} damage per second (per hit {per_hit:.2f}, every {interval}s)"]


def xp_table(base, growth, max_level):
    return json.dumps({str(l): round(base * growth ** (l - 2)) if l > 1 else 0 for l in range(1, max_level + 1)}, indent=2).splitlines()


def drop_check(path):
    weights = json.load(open(path, encoding="utf-8"))
    total = sum(weights.values())
    verdict = "ok" if math.isclose(total, 100, rel_tol=1e-6) or math.isclose(total, 1, rel_tol=1e-6) else "does not total 100 or 1"
    return [f"items: {len(weights)}, total weight: {total:g} ({verdict})"]


def loot_sim(path, trials, seed=1):
    weights = json.load(open(path, encoding="utf-8"))
    names = list(weights)
    rng = random.Random(seed)
    counts = Counter(rng.choices(names, weights=[weights[n] for n in names])[0] for _ in range(trials))
    total_w = sum(weights.values())
    rows = []
    for n in names:
        expected = weights[n] / total_w * 100
        got = counts[n] / trials * 100
        rows.append(f"{n:<20} expected {expected:6.2f}%  simulated {got:6.2f}%")
    return rows


def economy_check(path, lo=0.5, hi=2.0):
    items = json.load(open(path, encoding="utf-8"))
    rows = []
    for it in items:
        if it.get("value"):
            ratio = it["price"] / it["value"]
            if not lo <= ratio <= hi:
                rows.append(f"{it['name']}: price/value {ratio:.2f} (band {lo}-{hi})")
    return rows or ["all prices inside the band"]


# ---- levels and assets ----

def level_check(path):
    level = json.load(open(path, encoding="utf-8"))
    rooms = level.get("rooms", {})
    locks = level.get("locked", {})        # "a->b": "key_id"
    keys_in = level.get("keys", {})        # room: [key_id, ...]
    start, exit_room = level.get("start"), level.get("exit")
    have, seen = set(), {start}
    changed = True
    while changed:
        changed = False
        frontier = list(seen)
        for room in frontier:
            have.update(keys_in.get(room, []))
            for nxt in rooms.get(room, []):
                lock = locks.get(f"{room}->{nxt}")
                if nxt not in seen and (lock is None or lock in have):
                    seen.add(nxt)
                    changed = True
    rows = []
    all_rooms = set(rooms) | {x for v in rooms.values() for x in v}
    for room in sorted(all_rooms - seen):
        rows.append(f"unreachable: {room}")
    if exit_room and exit_room not in seen:
        rows.append(f"exit '{exit_room}' cannot be reached (locks need keys no reachable room holds)")
    return rows or [f"all {len(seen)} rooms reachable, exit reachable"]


REF = re.compile(r"[\"'(]([^\"'()\s]+\.(?:png|jpe?g|gif|webp|wav|ogg|mp3|ttf|otf|json|tscn|tres))[\"')]", re.I)


def asset_audit(root):
    refs = set()
    assets = {}
    for path in walk(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if path.lower().endswith(ASSET_EXT) and "/assets/" in "/" + rel:
            assets[rel] = path
        if path.lower().endswith((".py", ".js", ".ts", ".gd", ".cs", ".json", ".tscn", ".html")):
            refs.update(REF.findall(read_text(path)))
    rows = []
    for ref in sorted(refs):
        clean = ref.lstrip("./").replace("res://", "")
        if not os.path.exists(os.path.join(root, clean)):
            rows.append(f"missing: {ref}")
    referenced = {r.lstrip("./").replace("res://", "") for r in refs}
    for rel in sorted(assets):
        if not any(rel.endswith(r) or r.endswith(rel) for r in referenced):
            rows.append(f"unused: {rel}")
    return rows or ["no missing or unused assets"]


def asset_size(root, top=10):
    sizes = []
    for path in walk(root):
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".wav", ".ogg", ".mp3", ".webp")):
            sizes.append((os.path.getsize(path), os.path.relpath(path, root)))
    sizes.sort(reverse=True)
    total = sum(s for s, _ in sizes)
    rows = [f"{s / 1048576:8.2f} MB  {p}" for s, p in sizes[:top]]
    return rows + [f"total: {total / 1048576:.2f} MB in {len(sizes)} file(s)"]


def spritesheet(path, frame_w, frame_h):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return ["not a PNG file"]
    w, h = struct.unpack(">II", head[16:24])
    cols, rows_n = w // frame_w, h // frame_h
    left_w, left_h = w % frame_w, h % frame_h
    out = [f"image {w}x{h}: {cols} x {rows_n} = {cols * rows_n} frame(s) of {frame_w}x{frame_h}"]
    if left_w or left_h:
        out.append(f"note: {left_w}px right and {left_h}px bottom do not fill a frame")
    return out


def localization(root):
    used = set()
    locales = {}
    for path in walk(root):
        if path.lower().endswith((".py", ".js", ".ts", ".gd", ".cs")):
            used.update(re.findall(r"\b(?:t|tr|translate|Tr)\(\s*[\"']([\w.]+)[\"']", read_text(path)))
        if "locale" in path.lower() and path.lower().endswith(".json"):
            try:
                locales[os.path.relpath(path, root)] = set(json.load(open(path, encoding="utf-8")).keys())
            except (ValueError, AttributeError):
                continue
    rows = []
    for name, keys in locales.items():
        missing = sorted(used - keys)
        if missing:
            rows.append(f"{name}: missing {len(missing)} key(s), e.g. {', '.join(missing[:5])}")
    return rows or (["all used keys present"] if locales else ["no locale JSON files found"])


# ---- code checks ----

def rng_seed(root):
    rows = []
    for path in walk(root):
        if not path.endswith((".py", ".js", ".ts", ".gd", ".cs")):
            continue
        text = read_text(path)
        if re.search(r"\brandom\.|Math\.random\(|randi\(|randf\(|Random\(\)", text) and not re.search(r"seed|srand|RandomNumberGenerator", text, re.I):
            rows.append(f"{os.path.relpath(path, root)}: random calls with no seed in this file (replays will differ)")
    return rows or ["every file that uses randomness sets a seed"]


def save_format(root):
    rows = []
    for path in walk(root):
        if re.search(r"save", os.path.basename(path), re.I) and path.endswith(".json"):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except ValueError:
                rows.append(f"{os.path.relpath(path, root)}: not valid JSON")
                continue
            if not (isinstance(data, dict) and "version" in data):
                rows.append(f"{os.path.relpath(path, root)}: no version field")
    return rows or ["all save files carry a version"]


def golden_diff(actual, golden):
    a = json.load(open(actual, encoding="utf-8"))
    g = json.load(open(golden, encoding="utf-8"))
    rows = []

    def cmp(x, y, where):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                cmp(x.get(k), y.get(k), f"{where}.{k}" if where else k)
        elif x != y:
            rows.append(f"{where or '(root)'}: {y!r} -> {x!r}")

    cmp(a, g, "")
    return rows or ["identical to golden"]


# ---- playtesting and design ----

PLAY_FIELDS = ["date", "build", "minutes", "severity", "note"]


def playtest_log(path, build, minutes, severity, note):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, PLAY_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": dt.date.today().isoformat(), "build": build, "minutes": minutes,
                    "severity": severity, "note": note})
    return [f"logged to {path}"]


def playtest_summary(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    minutes = sum(float(r["minutes"] or 0) for r in rows)
    by_sev = Counter(r["severity"] for r in rows)
    out = [f"{len(rows)} session(s), {minutes:.0f} minutes played"]
    out += [f"{sev}: {n}" for sev, n in by_sev.most_common()]
    return out


def design_doc(title):
    sections = ["Overview", "Core loop", "Player goals", "Systems", "Progression", "Economy",
                "Levels", "Art and audio direction", "UI and controls", "Milestones", "Open questions"]
    return [f"# {title} -- Game Design Document", ""] + [f"## {s}\n\nTODO" for s in sections]


# ---- CLI ----

def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, a = argv[0], argv[1:]
    root = os.getcwd()
    try:
        if cmd == "balance-curve":
            rows = balance_curve(float(a[0]), float(a[1]), int(a[2]))
        elif cmd == "dps":
            rows = dps(float(a[0]), float(a[1]), *(float(x) for x in a[2:5]))
        elif cmd == "xp-table":
            rows = xp_table(float(a[0]), float(a[1]), int(a[2]))
        elif cmd == "drop-check":
            rows = drop_check(a[0])
        elif cmd == "loot-sim":
            rows = loot_sim(a[0], int(a[1]), int(a[2]) if len(a) > 2 else 1)
        elif cmd == "economy-check":
            rows = economy_check(a[0], *(float(x) for x in a[1:3]))
        elif cmd == "level-check":
            rows = level_check(a[0])
        elif cmd == "asset-audit":
            rows = asset_audit(a[0] if a else root)
        elif cmd == "asset-size":
            rows = asset_size(a[0] if a else root, int(a[1]) if len(a) > 1 else 10)
        elif cmd == "spritesheet":
            rows = spritesheet(a[0], int(a[1]), int(a[2]))
        elif cmd == "localization":
            rows = localization(a[0] if a else root)
        elif cmd == "rng-seed":
            rows = rng_seed(a[0] if a else root)
        elif cmd == "save-format":
            rows = save_format(a[0] if a else root)
        elif cmd == "playtest-log":
            rows = playtest_log(a[0], a[1], a[2], a[3], " ".join(a[4:]))
        elif cmd == "playtest-summary":
            rows = playtest_summary(a[0])
        elif cmd == "design-doc":
            rows = design_doc(" ".join(a))
        elif cmd == "golden-diff":
            rows = golden_diff(a[0], a[1])
        elif cmd in ("engine-detect", "godot-scenes", "unity-meta", "web-assets", "web-bundle-size"):
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import game_engines
            rows = game_engines.COMMANDS[cmd](a[0] if a else root)
        else:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import game_more
            if cmd not in game_more.COMMANDS:
                print(__doc__)
                return 2
            rows = game_more.run(cmd, a, root)
    except (IndexError, ValueError, OSError) as exc:
        print(f"game {cmd}: {exc}")
        return 2
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
