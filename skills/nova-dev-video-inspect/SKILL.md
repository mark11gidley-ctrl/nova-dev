---
name: nova-dev-video-inspect
description: Inspect a video: format, resolution, frame rate, codecs, loudness, silences and scene cuts. Use for "nova dev video inspect" or before editing a clip.
---

# Nova Dev Video Inspect

Run these on the file, then report the results in plain words:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" video probe <file>
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" video loudness <file>
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" video silence <file>
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/nd.py" video scenes <file>
```

Say what the file is, whether the loudness is usable online, and where the cuts and silences are, with times. Change nothing.
