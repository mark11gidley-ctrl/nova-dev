"""Self-check for the 19 extra game tools: python -I tests/test_game_more.py  (exits 0 on success)."""
import json
import os
import shutil
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import game_more as M  # noqa: E402
import game_tools  # noqa: E402

work = tempfile.mkdtemp(prefix="nd-gm-")
def put(rel, text):
    p = os.path.join(work, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)
def jp(rel, obj):
    put(rel, json.dumps(obj))
    return os.path.join(work, rel)

# gameplay code
put("loop.py", "while True:\n    x = 1\n")
put("ok.py", "while True:\n    clock.tick(60)\n")
assert any("loop.py" in r for r in M.frame_loop_check(work)) and not any("ok.py" in r for r in M.frame_loop_check(work))
put("keys.py", 'if is_action_pressed("jump"):\n    pass\nif is_action_pressed("fly"):\n    pass\n')
keys = jp("keys.json", ["jump"])
assert any("fly" in r for r in M.input_map_check(keys, work))
put("player.py", "speed = 350\nx = 0\n")
assert any("350" in r for r in M.gameplay_numbers(work))

# levels and progression
assert any("dead ends" in r for r in M.level_stats(jp("lv.json", {"rooms": {"a": ["b"], "b": []}, "exit": "z"})))
waves = jp("waves.json", [{"enemies": {"rat": 2}}, {"enemies": {"rat": 4}}, {"enemies": {"rat": 8}}])
rows = M.wave_plan(waves)
assert rows[0] == "wave 1: 2 enemies" and "x2.00" in rows[-1], rows
assert any("cycle" in r for r in M.progression_check(jp("pt.json", {"a": {"requires": ["b"]}, "b": {"requires": ["a"]}})))
assert any("negative" in r for r in M.stat_sanity(jp("it.json", [{"name": "x", "health": -1}])))
assert any("missing quest 'nope'" in r for r in M.quest_check(jp("q.json", [{"id": "q1", "requires": ["nope"]}])))
assert any("dead end" in r for r in M.dialogue_check(jp("d.json", {"n1": {"next": ["n2"]}, "n2": {}})))

# assets
with wave.open(os.path.join(work, "beep.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b"\x00\x00" * 8000)
assert any("1.00 s" in r for r in M.audio_length(work))
put("assets/my hero.png", "x")
assert any("spaces" in r for r in M.asset_names(work))
put("assets/copy1.png", "same")
put("assets/copy2.png", "same")
assert any("copy1.png" in r and "copy2.png" in r for r in M.duplicate_assets(work))

# build and telemetry
assert "within budget" in M.build_budget(10, work)[0]
assert "OVER" in M.build_budget(0.0000001, work)[0]
logcsv = os.path.join(work, "p.csv")
open(logcsv, "w").write("date,build,minutes,severity,note\n2026-11-01,0.1,60,low,x\n2026-11-01,0.1,60,low,y\n")
assert any("2 sessions per hour" in r or "sessions per hour" in r for r in M.session_stats(logcsv))
put("crash.log", "Traceback (most recent call last):\n  ...\nValueError: bad\n")
assert any("ValueError" in r for r in M.crash_group(os.path.join(work, "crash.log"), work))

# engine code
put("Assets/Player.cs", "class Enemy {}")
assert any("no class named Player" in r for r in M.unity_class_names(work))
put("main.gd", "func _ready():\n    btn.pressed.connect(on_pressed)\n")
assert any("on_pressed" in r for r in M.godot_signals(work))

# the CLI reaches them through the game group
assert game_tools.main(["frame-loop-check", work]) == 0
assert game_tools.main(["not-a-tool"]) == 2

shutil.rmtree(work, ignore_errors=True)
print("game more: all checks passed")
