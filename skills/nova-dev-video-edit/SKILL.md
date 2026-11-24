---
name: nova-dev-video-edit
description: Edit a video: trim, join clips, change the frame shape, adjust speed, fade, and watermark, always checking the result. Use for "nova dev video edit" or any cut-and-join request.
---

# Nova Dev Video Edit

Work in this order and confirm each step with `video probe` on the output:

1. Inspect the inputs (`nova-dev-video-inspect`).
2. For several clips, write an edit list (`edit-check` validates it, `edit-render` renders it). Use this instead of many concat steps.
3. Change frame shape with `video aspect <in> <out> <w> <h> crop|pad` (crop loses edges, pad adds bars).
4. Speed, fades and watermarks: `video speed`, `video fade`, `video watermark`.
5. Re-encode outputs are frame accurate; keep the original files.

State the final length and the settings used. End with Skipped / Risk.
