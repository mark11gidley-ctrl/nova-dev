"""Video creation and editing tools. Usage: nd.py video <name> [args]

Inspect
  probe <file>                         duration, size, resolution, frame rate, codecs
  presets                              render presets (YouTube, Shorts, square, web)
  check <file> <preset>                does the file match a preset? lists each mismatch
  loudness <file>                      integrated loudness (LUFS), true peak, loudness range
  silence <file> [db] [min_s]          silent stretches, with start and length
  scenes <file> [threshold]            cut points where the picture changes sharply
  name-check <folder>                  video file names that break the naming convention

Edit
  trim <in> <out> <start> <end>        cut a section (re-encoded, frame accurate)
  concat <out> <file> <file> ...       join clips (re-encoded, so mixed formats are fine)
  aspect <in> <out> <w> <h> crop|pad   change the frame shape without stretching
  speed <in> <out> <factor>            faster or slower, with audio kept in pitch
  fade <in> <out> <fade_in_s> <fade_out_s>
  watermark <in> <image> <out> [corner]
  burn-subs <in> <srt> <out>           hard-code subtitles into the picture

Export
  thumbnail <in> <time> <out.png>      one still frame
  frames <in> <fps> <folder>           a PNG per frame at the given rate
  compress <in> <out> [crf]            H.264 + AAC, smaller file (crf 18 best to 28 smallest)
  extract-audio <in> <out>             .wav (uncompressed) or .mp3
  normalize <in> <out> [lufs]          loudness to target (default -14 LUFS, for online video)
  gif <in> <out> [width] [fps] [seconds]

Subtitles and timecodes
  srt-check <file.srt>                 broken cues, overlaps, long lines, reading speed
  srt-shift <in.srt> <out.srt> <seconds>
  srt-vtt <in.srt> <out.vtt>           WebVTT for the web
  timecode <value> [fps]               convert between seconds, HH:MM:SS.mmm and frames

Planning
  edit-check <edit.json>               check an edit list: files, in/out points, total length
  edit-render <edit.json> <out>        render an edit list to one file
  shotlist <shots.json>                shot list as a Markdown table with timing totals
"""
import csv
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from video_core import (PRESETS, VideoError, check_preset, format_timecode, parse_srt,  # noqa: E402
                        parse_timecode, probe, run_ff, shift_srt, srt_problems, srt_to_vtt, write_srt)

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".avi")
ENCODE = ["-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]


# ---- inspect ----

def cmd_probe(path):
    info = probe(path)
    v, a = info["video"], info["audio"]
    rows = [f"duration: {info['duration']:.2f} s  size: {info['size_mb']:.1f} MB"]
    rows.append(f"video: {v['codec']} {v['width']}x{v['height']} at {v['fps']:.2f} fps" if v else "video: none")
    rows.append(f"audio: {a['codec']} {a['rate']} Hz, {a['channels']} channel(s)" if a else "audio: none")
    return rows


def cmd_presets():
    return [f"{name:<13} {p['w']}x{p['h']} {p['fps']} fps  ({p['note']})" for name, p in PRESETS.items()]


def cmd_check(path, preset):
    if preset not in PRESETS:
        raise VideoError(f"unknown preset {preset}. Run: video presets")
    problems = check_preset(probe(path), preset)
    return [f"{os.path.basename(path)} matches {preset}"] if not problems else \
        [f"{os.path.basename(path)} does not match {preset}:"] + [f"  - {p}" for p in problems]


def _ebur(path):
    proc = run_ff(["-i", path, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    block = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not block:
        raise VideoError("no loudness measurement (the file may have no audio)")
    return json.loads(block[-1])


def cmd_loudness(path):
    m = _ebur(path)
    lufs = float(m["input_i"])
    verdict = "within the usual online target (-14 LUFS +/- 1)" if abs(lufs + 14) <= 1 else \
        "outside the usual online target (-14 LUFS); run normalize"
    return [f"integrated loudness: {lufs:.1f} LUFS", f"true peak: {float(m['input_tp']):.1f} dBTP",
            f"loudness range: {float(m['input_lra']):.1f} LU", verdict]


def cmd_silence(path, db=-35.0, min_s=0.5):
    proc = run_ff(["-i", path, "-af", f"silencedetect=noise={db}dB:d={min_s}", "-f", "null", "-"])
    starts = re.findall(r"silence_start: ([\d.]+)", proc.stderr)
    ends = re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", proc.stderr)
    rows = [f"{float(s):7.2f} s  for {float(d):5.2f} s" for s, (_, d) in zip(starts, ends)]
    return rows or [f"no silence longer than {min_s} s below {db} dB"]


def cmd_scenes(path, threshold=0.3):
    proc = run_ff(["-i", path, "-filter:v", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    times = re.findall(r"pts_time:([\d.]+)", proc.stderr)
    rows = [f"cut at {float(t):8.2f} s" for t in times]
    return rows or [f"no cuts found at threshold {threshold}"]


NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*_v\d{2}(?:_\d{8})?\.(?:mp4|mov|mkv|webm|avi)$")


def cmd_name_check(folder):
    rows = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(VIDEO_EXT):
            continue
        if not NAME.match(name):
            stem, ext = os.path.splitext(name.lower().replace(" ", "_"))
            stem = re.sub(r"[^a-z0-9_-]+", "_", stem).strip("_") or "project"
            if not re.search(r"_v\d{2}", stem):
                stem += "_v01"
            rows.append(f"{name}: expected like project_v01_20261124.mp4 (try {stem}{ext})")
    return rows or ["every video name follows project_vNN[_YYYYMMDD].ext"]


# ---- edit ----

def cmd_trim(src, out, start, end):
    s = parse_timecode(start)
    e = parse_timecode(end)
    if e <= s:
        raise VideoError("end must be after start")
    run_ff(["-i", src, "-ss", f"{s:.3f}", "-to", f"{e:.3f}"] + ENCODE + [out])
    return [f"trimmed {e - s:.2f} s -> {out}"]


def _video_norm(w, h):
    """Scale and pad one picture to the target size, square pixels, 30 fps: concat needs equal inputs."""
    return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,fps=30,format=yuv420p")


AUDIO_NORM = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"


def _target_size(first_file):
    v = probe(first_file)["video"]
    if not v:
        raise VideoError(f"{first_file} has no video stream")
    return v["width"] - v["width"] % 2, v["height"] - v["height"] % 2


def cmd_concat(out, *files):
    if len(files) < 2:
        raise VideoError("give at least two files")
    w, h = _target_size(files[0])
    args = []
    for f in files:
        args += ["-i", f]
    parts = []
    labels = []
    for i in range(len(files)):
        parts.append(f"[{i}:v:0]{_video_norm(w, h)}[v{i}];[{i}:a:0]{AUDIO_NORM}[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(files)}:v=1:a=1[v][a]"
    run_ff(args + ["-filter_complex", graph, "-map", "[v]", "-map", "[a]"] + ENCODE + [out])
    return [f"joined {len(files)} clips at {w}x{h} -> {out}"]


def cmd_aspect(src, out, w, h, mode):
    w, h = int(w), int(h)
    if mode == "crop":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    elif mode == "pad":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
    else:
        raise VideoError("mode must be crop or pad")
    run_ff(["-i", src, "-vf", vf, "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
    return [f"{w}x{h} ({mode}) -> {out}"]


def _atempo_chain(factor):
    parts = []
    f = factor
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5")
        f /= 0.5
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def cmd_speed(src, out, factor):
    f = float(factor)
    if f <= 0:
        raise VideoError("factor must be above 0")
    run_ff(["-i", src, "-filter_complex", f"[0:v]setpts=PTS/{f}[v];[0:a]{_atempo_chain(f)}[a]",
            "-map", "[v]", "-map", "[a]"] + ENCODE + [out])
    return [f"speed x{f} -> {out}"]


def cmd_fade(src, out, fade_in, fade_out):
    dur = probe(src)["duration"]
    fi, fo = float(fade_in), float(fade_out)
    if fi + fo > dur:
        raise VideoError(f"fades ({fi + fo} s) are longer than the clip ({dur:.2f} s)")
    vf = f"fade=t=in:st=0:d={fi},fade=t=out:st={dur - fo:.3f}:d={fo}"
    af = f"afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
    run_ff(["-i", src, "-vf", vf, "-af", af] + ENCODE + [out])
    return [f"fade in {fi} s, out {fo} s -> {out}"]


def cmd_watermark(src, image, out, corner="bottomright"):
    pos = {"topleft": "20:20", "topright": "W-w-20:20", "bottomleft": "20:H-h-20",
           "bottomright": "W-w-20:H-h-20", "center": "(W-w)/2:(H-h)/2"}
    if corner not in pos:
        raise VideoError(f"corner must be one of {', '.join(pos)}")
    run_ff(["-i", src, "-i", image, "-filter_complex", f"overlay={pos[corner]}", "-c:a", "copy"]
           + ["-c:v", "libx264", "-pix_fmt", "yuv420p", out])
    return [f"watermark at {corner} -> {out}"]


def cmd_burn_subs(src, srt, out):
    # ffmpeg's subtitle filter chokes on Windows paths, so copy the file next to a simple name first
    tmp = tempfile.mkdtemp(prefix="nd-subs-")
    try:
        shutil.copy(srt, os.path.join(tmp, "subs.srt"))
        run_ff(["-i", os.path.abspath(src), "-vf", "subtitles=subs.srt"] + ENCODE + [os.path.abspath(out)], cwd=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [f"subtitles burned in -> {out}"]


# ---- export ----

def cmd_thumbnail(src, time_text, out):
    run_ff(["-ss", f"{parse_timecode(time_text):.3f}", "-i", src, "-frames:v", "1", out])
    return [f"thumbnail -> {out}"]


def cmd_frames(src, fps, folder):
    os.makedirs(folder, exist_ok=True)
    run_ff(["-i", src, "-vf", f"fps={fps}", os.path.join(folder, "frame_%05d.png")])
    count = len([f for f in os.listdir(folder) if f.endswith(".png")])
    return [f"{count} frame(s) -> {folder}"]


def cmd_compress(src, out, crf=23):
    crf = int(crf)
    if not 0 <= crf <= 51:
        raise VideoError("crf must be between 0 and 51")
    before = os.path.getsize(src)
    run_ff(["-i", src, "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", out])
    after = os.path.getsize(out)
    return [f"{before / 1048576:.1f} MB -> {after / 1048576:.1f} MB ({after / before * 100:.0f}% of the original)"]


def cmd_extract_audio(src, out):
    if out.lower().endswith(".mp3"):
        run_ff(["-i", src, "-vn", "-c:a", "libmp3lame", "-q:a", "2", out])
    else:
        run_ff(["-i", src, "-vn", "-c:a", "pcm_s16le", out])
    return [f"audio -> {out}"]


def cmd_normalize(src, out, lufs=-14.0):
    m = _ebur(src)
    target = float(lufs)
    run_ff(["-i", src, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            "offset=" + str(m["target_offset"]) + ":linear=true",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out])
    return [f"normalized from {float(m['input_i']):.1f} to {target} LUFS -> {out}"]


def cmd_gif(src, out, width=480, fps=12, seconds=None):
    tmp = tempfile.mkdtemp(prefix="nd-gif-")
    try:
        palette = os.path.join(tmp, "palette.png")
        base = ["-i", src] + (["-t", str(seconds)] if seconds else [])
        vf = f"fps={fps},scale={int(width)}:-1:flags=lanczos"
        run_ff(base + ["-vf", f"{vf},palettegen", palette])
        run_ff(base + ["-i", palette, "-lavfi", f"{vf}[x];[x][1:v]paletteuse", out])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [f"gif -> {out} ({os.path.getsize(out) / 1048576:.2f} MB)"]


# ---- subtitles and timecodes ----

def _read_srt(path):
    with open(path, encoding="utf-8-sig") as fh:
        return parse_srt(fh.read())


def cmd_srt_check(path):
    return srt_problems(_read_srt(path))


def cmd_srt_shift(src, out, seconds):
    cues = shift_srt(_read_srt(src), float(seconds))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(write_srt(cues))
    return [f"shifted {len(cues)} cue(s) by {seconds} s -> {out}"]


def cmd_srt_vtt(src, out):
    cues = _read_srt(src)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(srt_to_vtt(cues))
    return [f"{sum(1 for c in cues if not c.get('error'))} cue(s) -> {out}"]


def cmd_timecode(value, fps=30.0):
    fps = float(fps)
    secs = parse_timecode(value, fps)
    return [f"{secs:.3f} seconds", f"{format_timecode(secs).replace(',', '.')}",
            f"frame {round(secs * fps)} at {fps:g} fps"]


# ---- planning ----

def _edit(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    base = os.path.dirname(os.path.abspath(path))
    clips = data.get("clips", [])
    if not clips:
        raise VideoError("the edit list has no clips")
    return data, base, clips


def cmd_edit_check(path):
    data, base, clips = _edit(path)
    rows = []
    total = 0.0
    for i, c in enumerate(clips, 1):
        f = os.path.join(base, c["file"])
        if not os.path.exists(f):
            rows.append(f"clip {i}: file missing: {c['file']}")
            continue
        s, e = parse_timecode(str(c["in"])), parse_timecode(str(c["out"]))
        if e <= s:
            rows.append(f"clip {i}: out point is not after the in point")
            continue
        dur = probe(f)["duration"]
        if e > dur + 0.01:
            rows.append(f"clip {i}: out point {e:.2f} s is past the end of the file ({dur:.2f} s)")
            continue
        total += e - s
    rows.append(f"{len(clips)} clip(s), total length {total:.2f} s")
    return rows


def cmd_edit_render(path, out):
    data, base, clips = _edit(path)
    missing = [c["file"] for c in clips if not os.path.exists(os.path.join(base, c["file"]))]
    if missing:
        raise VideoError(f"run edit-check first: missing {', '.join(missing)}")
    w, h = _target_size(os.path.join(base, clips[0]["file"]))
    args, parts, labels = [], [], []
    for i, c in enumerate(clips):
        args += ["-i", os.path.join(base, c["file"])]
        s_, e_ = parse_timecode(str(c["in"])), parse_timecode(str(c["out"]))
        parts.append(f"[{i}:v]trim=start={s_:.3f}:end={e_:.3f},setpts=PTS-STARTPTS,{_video_norm(w, h)}[v{i}];"
                     f"[{i}:a]atrim=start={s_:.3f}:end={e_:.3f},asetpts=PTS-STARTPTS,{AUDIO_NORM}[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    run_ff(args + ["-filter_complex", graph, "-map", "[v]", "-map", "[a]"] + ENCODE + [out])
    return [f"rendered {len(clips)} clip(s) at {w}x{h} -> {out}"]


def cmd_shotlist(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    shots = data.get("shots", [])
    target = data.get("target_seconds")
    rows = ["| # | Shot | Seconds | Camera | Location |", "|---|------|---------|--------|----------|"]
    total = 0.0
    problems = []
    for i, s in enumerate(shots, 1):
        sec = float(s.get("seconds", 0) or 0)
        total += sec
        if not s.get("description"):
            problems.append(f"shot {i}: no description")
        if sec <= 0:
            problems.append(f"shot {i}: no length")
        rows.append(f"| {i} | {s.get('description', '')} | {sec:g} | {s.get('camera', '')} | {s.get('location', '')} |")
    rows.append(f"\n**Total:** {total:g} seconds across {len(shots)} shot(s)")
    if target:
        rows.append(f"**Target:** {target} seconds ({total - float(target):+g} s)")
    return rows + [f"- {p}" for p in problems]


COMMANDS = {
    "probe": (cmd_probe, 1), "presets": (cmd_presets, 0), "check": (cmd_check, 2),
    "loudness": (cmd_loudness, 1), "silence": (cmd_silence, 1), "scenes": (cmd_scenes, 1),
    "name-check": (cmd_name_check, 1), "trim": (cmd_trim, 4), "concat": (cmd_concat, 2),
    "aspect": (cmd_aspect, 4), "speed": (cmd_speed, 3), "fade": (cmd_fade, 4),
    "watermark": (cmd_watermark, 3), "burn-subs": (cmd_burn_subs, 3), "thumbnail": (cmd_thumbnail, 3),
    "frames": (cmd_frames, 3), "compress": (cmd_compress, 2), "extract-audio": (cmd_extract_audio, 2),
    "normalize": (cmd_normalize, 2), "gif": (cmd_gif, 2), "srt-check": (cmd_srt_check, 1),
    "srt-shift": (cmd_srt_shift, 3), "srt-vtt": (cmd_srt_vtt, 2), "timecode": (cmd_timecode, 1),
    "edit-check": (cmd_edit_check, 1), "edit-render": (cmd_edit_render, 2), "shotlist": (cmd_shotlist, 1),
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    fn, min_args = COMMANDS[argv[0]]
    args = argv[1:]
    if len(args) < min_args:
        print(f"video {argv[0]} needs {min_args} argument(s). See: nd.py video help")
        return 2
    try:
        rows = fn(*args)
    except VideoError as exc:
        print(f"video {argv[0]}: {exc}")
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"video {argv[0]}: {exc}")
        return 1
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
