"""Self-check: python -I tests/test_codex.py  (exits 0 on success).
Checks the Codex plugin manifest and hook file point at things that exist, and that the hook
commands use the cross-shell Node launcher."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
manifest = json.load(open(os.path.join(ROOT, ".codex-plugin", "plugin.json"), encoding="utf-8"))
assert manifest["name"] == "nova-dev"
assert os.path.isdir(os.path.join(ROOT, manifest["skills"]))
hooks_path = os.path.join(ROOT, manifest["hooks"])
assert os.path.isfile(hooks_path), manifest["hooks"]
for event, groups in json.load(open(hooks_path, encoding="utf-8"))["hooks"].items():
    for group in groups:
        for h in group["hooks"]:
            assert "launch.js" in h["command"], h["command"]       # cross-shell launcher, no shell operators
            assert "||" not in h["command"] and "${" not in h["command"].split('"')[-1]
            script = h["command"].split()[-1]
            assert os.path.isfile(os.path.join(ROOT, "hooks", script)), script
assert os.path.isfile(os.path.join(ROOT, "hooks", "launch.js"))
print("codex: all checks passed")
