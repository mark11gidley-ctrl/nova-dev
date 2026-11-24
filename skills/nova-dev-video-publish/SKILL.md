---
name: nova-dev-video-publish
description: Prepare a video for publishing: check it against a platform preset, normalize loudness, compress, check the file name, and export a thumbnail. Use for "nova dev video publish" or before uploading.
---

# Nova Dev Video Publish

1. `video presets` to choose a target, then `video check <file> <preset>`.
2. `video loudness <file>`; if it is outside the online target, `video normalize <file> <out>`.
3. `video compress <file> <out> 23` for a smaller upload (lower crf means better quality and a bigger file).
4. `video name-check <folder>` for the file naming convention.
5. `video thumbnail <file> <time> <out.png>` for a cover frame.

Report the final file, its size, and each check's result. End with Skipped / Risk.
