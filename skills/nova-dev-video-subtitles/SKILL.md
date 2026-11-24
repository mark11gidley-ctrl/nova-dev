---
name: nova-dev-video-subtitles
description: Make and check subtitles: validate an SRT file, shift timing, convert to WebVTT, and burn subtitles into a video. Use for "nova dev subtitles" or captioning a video.
---

# Nova Dev Video Subtitles

1. Check the file: `video srt-check <file.srt>`. Fix every reported cue (overlaps, lines over 42 characters, reading speed over 17 characters per second) before going further.
2. Shift the timing if the video starts late: `video srt-shift <in> <out> <seconds>`.
3. For the web, `video srt-vtt <in.srt> <out.vtt>`.
4. To hard-code captions, `video burn-subs <video> <srt> <out>`. Burned subtitles cannot be turned off, so say so.

Use `video timecode` to convert a time from a video editor (frames or HH:MM:SS).
