"""Self-check for the video tools: python -I tests/test_video.py  (exits 0 on success).

Pure-Python checks always run. Real-video checks run when ffmpeg is installed and say so when it is not."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import video_core as C  # noqa: E402
import video_tools as T  # noqa: E402

work = tempfile.mkdtemp(prefix="nd-video-")

# ---- timecodes ----
assert C.parse_timecode("00:01:02.500") == 62.5
assert C.parse_timecode("1:02") == 62.0
assert C.parse_timecode("00:01:02:15", 30) == 62.5
assert C.parse_timecode("12.25") == 12.25
assert C.format_timecode(62.5) == "00:01:02,500"
assert C.to_frames(62.5, 30) == 1875
try:
    C.parse_timecode("soon")
    raise AssertionError("bad timecode accepted")
except C.VideoError:
    pass

# ---- subtitles ----
srt = ("1\n00:00:00,000 --> 00:00:01,500\nHello there\n\n"
       "2\n00:00:01,000 --> 00:00:02,000\nOverlap here\n\n"
       "3\n00:00:03,000 --> 00:00:02,500\nBackwards\n\n"
       "4\nnot a timing line\nx\n")
cues = C.parse_srt(srt)
assert len(cues) == 4 and cues[0]["start"] == 0.0 and cues[0]["end"] == 1.5
problems = C.srt_problems(cues)
assert any("overlaps" in p for p in problems) and any("ends before" in p for p in problems)
assert any("cue 4" in p and "timing" in p for p in problems)
long_line = [{"start": 0, "end": 5, "lines": ["x" * 50], "index": None, "error": None}]
assert any("line of 50" in p for p in C.srt_problems(long_line))
fast = [{"start": 0, "end": 1, "lines": ["a" * 40], "index": None, "error": None}]
assert any("characters per second" in p for p in C.srt_problems(fast))
ok = C.parse_srt("1\n00:00:00,000 --> 00:00:02,000\nFine line\n")
assert C.srt_problems(ok) == ["subtitles pass every check"]
shifted = C.shift_srt(ok, 1.5)
assert abs(shifted[0]["start"] - 1.5) < 1e-9 and abs(shifted[0]["end"] - 3.5) < 1e-9
assert "00:00:01.500 --> 00:00:03.500" in C.srt_to_vtt(shifted)
assert C.write_srt(shifted).startswith("1\n00:00:01,500 --> 00:00:03,500")

# ---- presets ----
info = {"video": {"codec": "h264", "width": 1080, "height": 1920, "fps": 30.0},
        "audio": {"codec": "aac", "rate": 48000, "channels": 2}}
assert C.check_preset(info, "shorts") == []
assert any("size" in p for p in C.check_preset(info, "youtube-1080"))
assert C.check_preset({"video": None, "audio": None}, "shorts") == ["no video stream"]

# ---- naming and shot list ----
os.makedirs(os.path.join(work, "videos"))
for name in ("launch_v01_20261124.mp4", "My Clip.mov", "notes.txt"):
    open(os.path.join(work, "videos", name), "w").close()
names = T.cmd_name_check(os.path.join(work, "videos"))
assert len(names) == 1 and "My Clip.mov" in names[0] and "my_clip_v01.mov" in names[0], names
shots = os.path.join(work, "shots.json")
open(shots, "w").write(json.dumps({"target_seconds": 10, "shots": [
    {"description": "Open", "seconds": 4, "camera": "wide", "location": "hall"},
    {"description": "", "seconds": 0}]}))
rows = T.cmd_shotlist(shots)
assert any("Total:** 4 seconds" in r for r in rows) and any("Target" in r for r in rows)
assert any("shot 2: no description" in r for r in rows)

# ---- CLI dispatch ----
assert T.main(["not-a-command"]) == 2
assert T.main(["trim"]) == 2  # too few arguments
assert T.main(["timecode", "00:00:10", "25"]) == 0

# ---- real video (needs ffmpeg) ----
if not shutil.which("ffmpeg") and not os.path.exists(r"C:\Users\Forge PC User\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"):
    print("video: ffmpeg not found, real-video checks skipped")
else:
    if not shutil.which("ffmpeg"):
        os.environ["PATH"] += os.pathsep + r"C:\Users\Forge PC User\AppData\Local\Microsoft\WinGet\Links"
    v = os.path.join(work, "a.mp4")
    w2 = os.path.join(work, "b.mov")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=640x360:rate=30:duration=4", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", v],
                   check=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=25:duration=3", "-f", "lavfi", "-i",
                    "sine=frequency=880:duration=3", "-c:v", "libx264", "-c:a", "aac", w2], check=True)

    info = C.probe(v)
    assert info["video"]["width"] == 640 and abs(info["duration"] - 4) < 0.1
    assert T.cmd_probe(v)[1].startswith("video: h264 640x360")
    assert any("does not match" in r for r in T.cmd_check(v, "youtube-1080"))
    assert "trimmed 2.00 s" in T.cmd_trim(v, os.path.join(work, "t.mp4"), "1", "3")[0]
    assert "joined 2 clips" in T.cmd_concat(os.path.join(work, "j.mp4"), v, w2)[0]
    joined = C.probe(os.path.join(work, "j.mp4"))
    assert joined["video"]["width"] == 640 and joined["audio"]["rate"] == 48000
    assert "1080x1920" in T.cmd_aspect(w2, os.path.join(work, "p.mp4"), 1080, 1920, "pad")[0]
    assert abs(C.probe(os.path.join(work, "p.mp4"))["video"]["height"] - 1920) < 2
    T.cmd_speed(v, os.path.join(work, "f.mp4"), 2)
    assert 1.8 < C.probe(os.path.join(work, "f.mp4"))["duration"] < 2.3
    T.cmd_fade(v, os.path.join(work, "fd.mp4"), 0.5, 0.5)
    assert T.cmd_loudness(v)[0].startswith("integrated loudness")
    T.cmd_normalize(v, os.path.join(work, "n.mp4"))
    T.cmd_thumbnail(v, "1.5", os.path.join(work, "th.png"))
    assert os.path.getsize(os.path.join(work, "th.png")) > 0
    T.cmd_gif(v, os.path.join(work, "g.gif"), 240, 8, 1)
    T.cmd_compress(w2, os.path.join(work, "c.mp4"), 30)
    T.cmd_extract_audio(v, os.path.join(work, "a.wav"))
    assert C.probe(os.path.join(work, "a.wav"))["duration"] > 3.5
    srt_path = os.path.join(work, "s.srt")
    open(srt_path, "w", encoding="utf-8").write(srt)
    T.cmd_burn_subs(v, srt_path, os.path.join(work, "burned.mp4"))
    assert C.probe(os.path.join(work, "burned.mp4"))["video"] is not None
    assert T.cmd_frames(v, 5, os.path.join(work, "frames"))[0].startswith("20 frame(s)")
    open(os.path.join(work, "edit.json"), "w").write(json.dumps({"clips": [
        {"file": "a.mp4", "in": "0.5", "out": "2"}, {"file": "b.mov", "in": "0", "out": "1.5"}]}))
    assert "total length 3.00 s" in T.cmd_edit_check(os.path.join(work, "edit.json"))[-1]
    assert "rendered 2 clip(s)" in T.cmd_edit_render(os.path.join(work, "edit.json"), os.path.join(work, "e.mp4"))[0]
    assert 2.8 < C.probe(os.path.join(work, "e.mp4"))["duration"] < 3.3
    open(os.path.join(work, "bad.json"), "w").write(json.dumps({"clips": [{"file": "gone.mp4", "in": "0", "out": "1"}]}))
    assert any("file missing" in r for r in T.cmd_edit_check(os.path.join(work, "bad.json")))

shutil.rmtree(work, ignore_errors=True)
print("video tools: all checks passed")
