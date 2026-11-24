"""Self-check for the game tools: python -I tests/test_game.py  (exits 0 on success)."""
import json
import os
import shutil
import struct
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import game_tools as G  # noqa: E402
import game_engines as E  # noqa: E402

work = tempfile.mkdtemp(prefix="nd-game-")
w = lambda p, t: (os.makedirs(os.path.dirname(os.path.join(work, p)), exist_ok=True), open(os.path.join(work, p), "w", encoding="utf-8").write(t))  # noqa: E731

# balance and economy
assert any("jump over 2x" in r for r in G.balance_curve(10, 2.5, 4))
assert "per hit" in G.dps(10, 1, 0.5, 2, 20)[0] and "6.00" in G.dps(10, 1, 0, 2, 40)[0]
assert json.loads("\n".join(G.xp_table(100, 2, 3)))["3"] == 200
w("drops.json", json.dumps({"gold": 60, "gem": 30, "potion": 10}))
assert "ok" in G.drop_check(os.path.join(work, "drops.json"))[0]
w("bad.json", json.dumps({"a": 60}))
assert "does not total" in G.drop_check(os.path.join(work, "bad.json"))[0]
sim = G.loot_sim(os.path.join(work, "drops.json"), 20000, seed=3)
assert all(abs(float(r.split("simulated")[1].split("%")[0]) - float(r.split("expected")[1].split("%")[0])) < 2 for r in sim), sim
w("items.json", json.dumps([{"name": "sword", "price": 100, "value": 10}, {"name": "rock", "price": 5, "value": 5}]))
assert any("sword" in r for r in G.economy_check(os.path.join(work, "items.json")))

# levels: a locked exit with no key is reported; with the key, it is reachable
w("lvl.json", json.dumps({"start": "a", "exit": "z", "rooms": {"a": ["b"], "b": ["z"]},
                          "locked": {"b->z": "gold_key"}, "keys": {}}))
assert any("cannot be reached" in r for r in G.level_check(os.path.join(work, "lvl.json")))
w("lvl2.json", json.dumps({"start": "a", "exit": "z", "rooms": {"a": ["b"], "b": ["z"]},
                           "locked": {"b->z": "gold_key"}, "keys": {"a": ["gold_key"]}}))
assert "exit reachable" in G.level_check(os.path.join(work, "lvl2.json"))[0]

# assets: a missing reference is reported, a present one is not
w("src/main.py", 'img = load("assets/hero.png")\nsnd = load("assets/missing.wav")\n')
w("assets/hero.png", "x")
audit = G.asset_audit(work)
assert any("missing: assets/missing.wav" in r for r in audit), audit
assert not any("hero.png" in r and "missing" in r for r in audit)

# spritesheet from a real PNG header
png = os.path.join(work, "sheet.png")
ihdr = struct.pack(">II", 64, 32) + bytes([8, 6, 0, 0, 0])
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
open(png, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr))
assert "8 frame(s)" in G.spritesheet(png, 16, 16)[0]

# localization: keys used in code and missing from the locale file
w("src/ui.py", 't("menu.start")\nt("menu.quit")\n')
w("locale/en.json", json.dumps({"menu.start": "Start"}))
assert any("missing 1 key" in r and "menu.quit" in r for r in G.localization(work))

# code checks and saves
w("src/rng.py", "import random\nx = random.random()\n")
assert any("rng.py" in r for r in G.rng_seed(work))
w("saves/save1.json", json.dumps({"gold": 5}))
assert any("no version" in r for r in G.save_format(work))

# golden diff
w("a.json", json.dumps({"hp": 5, "pos": {"x": 1}}))
w("g.json", json.dumps({"hp": 6, "pos": {"x": 1}}))
assert any("hp" in r for r in G.golden_diff(os.path.join(work, "a.json"), os.path.join(work, "g.json")))

# playtest log and summary
log = os.path.join(work, "play.csv")
G.playtest_log(log, "0.1", "30", "high", "crash on level 2")
G.playtest_log(log, "0.1", "15", "low", "slow menu")
assert any("2 session(s)" in r and "45 minutes" in r for r in G.playtest_summary(log))

# design doc skeleton has the standard sections
assert any(l.startswith("## Core loop") for l in G.design_doc("Game").__iter__())

# engines: detection, Godot resource refs, Unity meta, web references
w("project.godot", "[application]\n")
assert "Godot" in E.engine_detect(work)[0]
w("scenes/main.tscn", '[ext_resource path="res://art/missing.png" type="Texture"]\n')
assert any("art/missing.png" in r for r in E.godot_scenes(work))
w("Assets/Player.cs", "class P {}")
w("ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 2022")
assert any("no .meta: Assets" in r for r in E.unity_meta(work))
w("index.html", '<script src="game.js"></script><img src="gone.png">')
w("game.js", "")
assert any("gone.png" in r for r in E.web_assets(work))

shutil.rmtree(work, ignore_errors=True)
print("game tools: all checks passed")
