"""Shared helpers for the video tools: ffmpeg/ffprobe calls, presets, timecodes, and SRT subtitles.

Everything here is pure Python except run_ff and probe, which call ffmpeg and ffprobe."""
import json
import re
import shutil
import subprocess
from fractions import Fraction


class VideoError(Exception):
    """Raised with a short, readable message when ffmpeg or the input is the problem."""


def _tool(name):
    path = shutil.which(name)
    if not path:
        raise VideoError(f"{name} is not installed or not on PATH. Install ffmpeg (winget install Gyan.FFmpeg).")
    return path


def run_ff(args, cwd=None):
    """Run ffmpeg with -y -hide_banner. Returns the process; stderr holds the log ffmpeg prints."""
    proc = subprocess.run([_tool("ffmpeg"), "-y", "-hide_banner"] + args, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-4:])
        raise VideoError(f"ffmpeg failed: {tail}")
    return proc


def probe(path):
    """Summary of a media file: duration, size, frame rate, codecs, audio layout."""
    proc = subprocess.run([_tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_format",
                           "-show_streams", path], capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoError(f"cannot read {path}: {proc.stderr.strip()[:200]}")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    info = {
        "duration": float(fmt.get("duration", 0) or 0),
        "size_mb": int(fmt.get("size", 0) or 0) / 1048576,
        "video": None,
        "audio": None,
    }
    if v:
        info["video"] = {
            "codec": v.get("codec_name"),
            "width": int(v.get("width", 0)),
            "height": int(v.get("height", 0)),
            "fps": float(fps_of(v.get("avg_frame_rate") or v.get("r_frame_rate") or "0")),
        }
    if a:
        info["audio"] = {"codec": a.get("codec_name"), "rate": int(a.get("sample_rate", 0) or 0),
                         "channels": int(a.get("channels", 0) or 0)}
    return info


def fps_of(rate):
    try:
        return float(Fraction(rate)) if rate not in ("0", "0/0", "") else 0.0
    except (ZeroDivisionError, ValueError):
        return 0.0


PRESETS = {
    "youtube-1080": {"w": 1920, "h": 1080, "fps": 30, "vcodec": "h264", "acodec": "aac", "note": "landscape HD"},
    "youtube-4k": {"w": 3840, "h": 2160, "fps": 30, "vcodec": "h264", "acodec": "aac", "note": "4K landscape"},
    "shorts": {"w": 1080, "h": 1920, "fps": 30, "vcodec": "h264", "acodec": "aac", "note": "vertical 9:16"},
    "square": {"w": 1080, "h": 1080, "fps": 30, "vcodec": "h264", "acodec": "aac", "note": "1:1 feed"},
    "web-720": {"w": 1280, "h": 720, "fps": 30, "vcodec": "h264", "acodec": "aac", "note": "small web"},
}


def check_preset(info, preset):
    """Compare a probe result with a preset. Returns a list of mismatches (empty means it matches)."""
    p = PRESETS[preset]
    v, a = info.get("video"), info.get("audio")
    problems = []
    if not v:
        return ["no video stream"]
    if (v["width"], v["height"]) != (p["w"], p["h"]):
        problems.append(f"size {v['width']}x{v['height']} (want {p['w']}x{p['h']})")
    if abs(v["fps"] - p["fps"]) > 0.05:
        problems.append(f"frame rate {v['fps']:.2f} (want {p['fps']})")
    if v["codec"] != p["vcodec"]:
        problems.append(f"video codec {v['codec']} (want {p['vcodec']})")
    if a is None:
        problems.append("no audio stream")
    elif a["codec"] != p["acodec"]:
        problems.append(f"audio codec {a['codec']} (want {p['acodec']})")
    return problems


# ---- timecodes ----

def parse_timecode(text, fps=30.0):
    """Accepts 'HH:MM:SS.mmm', 'MM:SS', 'HH:MM:SS:FF' (frames) or plain seconds. Returns seconds."""
    text = text.strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+)(?:[.,](\d+)|:(\d+))?", text)
    if not m:
        raise VideoError(f"not a timecode: {text}")
    h, mi, s, frac, frames = m.groups()
    secs = int(h or 0) * 3600 + int(mi) * 60 + int(s)
    if frac is not None:
        secs += float("0." + frac)
    if frames is not None:
        secs += int(frames) / fps
    return secs


def format_timecode(seconds):
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3600000)
    mi, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def to_frames(seconds, fps):
    return round(seconds * fps)


# ---- SRT subtitles ----

TIME = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def _secs(m):
    h, mi, s, ms = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def parse_srt(text):
    """Returns a list of cues: {index, start, end, lines}. Malformed blocks become cues with 'error'."""
    cues = []
    blocks = re.split(r"\r?\n\r?\n+", text.strip())
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip() != ""]
        if not lines:
            continue
        cue = {"index": None, "start": None, "end": None, "lines": [], "error": None}
        idx = 0
        if "-->" not in lines[0]:
            cue["index"] = lines[0].strip()
            idx = 1
        if idx >= len(lines) or "-->" not in lines[idx]:
            cue["error"] = "missing timing line"
            cues.append(cue)
            continue
        left, _, right = lines[idx].partition("-->")
        a, b = TIME.search(left), TIME.search(right)
        if not a or not b:
            cue["error"] = "bad timestamp"
            cues.append(cue)
            continue
        cue["start"], cue["end"] = _secs(a), _secs(b)
        cue["lines"] = lines[idx + 1:]
        cues.append(cue)
    return cues


def write_srt(cues):
    out = []
    for n, c in enumerate(cues, 1):
        out.append(str(n))
        out.append(f"{format_timecode(c['start'])} --> {format_timecode(c['end'])}")
        out.extend(c["lines"])
        out.append("")
    return "\n".join(out)


def srt_problems(cues, max_line=42, max_cps=17.0):
    """Subtitle checks: broken cues, bad order, overlaps, long lines, reading speed."""
    rows = []
    prev_end = None
    for n, c in enumerate(cues, 1):
        if c.get("error"):
            rows.append(f"cue {n}: {c['error']}")
            continue
        if c["end"] <= c["start"]:
            rows.append(f"cue {n}: ends before it starts")
        if prev_end is not None and c["start"] < prev_end:
            rows.append(f"cue {n}: overlaps the previous cue")
        if prev_end is not None and c["start"] < prev_end - 60:
            rows.append(f"cue {n}: starts far before the previous cue ends")
        for line in c["lines"]:
            if len(line) > max_line:
                rows.append(f"cue {n}: line of {len(line)} characters (limit {max_line})")
        if len(c["lines"]) > 2:
            rows.append(f"cue {n}: {len(c['lines'])} lines (limit 2)")
        dur = c["end"] - c["start"]
        chars = sum(len(l.replace(" ", "")) for l in c["lines"])
        if dur > 0 and chars / dur > max_cps:
            rows.append(f"cue {n}: reads at {chars / dur:.0f} characters per second (limit {max_cps:.0f})")
        prev_end = c["end"]
    return rows or ["subtitles pass every check"]


def shift_srt(cues, seconds):
    out = []
    for c in cues:
        if c.get("error"):
            out.append(c)
            continue
        s, e = c["start"] + seconds, c["end"] + seconds
        if s < 0:
            s, e = 0.0, max(0.0, e)
        out.append(dict(c, start=s, end=e))
    return out


def srt_to_vtt(cues):
    out = ["WEBVTT", ""]
    for c in cues:
        if c.get("error"):
            continue
        out.append(f"{format_timecode(c['start']).replace(',', '.')} --> {format_timecode(c['end']).replace(',', '.')}")
        out.extend(c["lines"])
        out.append("")
    return "\n".join(out)
