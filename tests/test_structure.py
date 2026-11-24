"""Self-check: python -I tests/test_structure.py  (exits 0 on success)."""
import json
import os
import re
import subprocess
import sys

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

manifest = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8"))
assert manifest["name"] == "nova-dev"

skills = os.path.join(root, "skills")
expected = set(os.listdir(skills))
assert len(expected) >= 32, sorted(expected)
assert all(name.startswith("nova-dev") for name in expected), expected
for name in expected:
    text = open(os.path.join(skills, name, "SKILL.md"), encoding="utf-8").read()
    front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert front, f"{name}: needs frontmatter"
    assert re.search(rf"^name: {re.escape(name)}$", front.group(1), re.M), name
    assert re.search(r"^description: .+", front.group(1), re.M), name

hooks = json.load(open(os.path.join(root, "hooks", "hooks.json"), encoding="utf-8"))
for groups in hooks["hooks"].values():
    for group in groups:
        for h in group["hooks"]:
            script = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"", h["command"]).group(1)
            assert os.path.isfile(os.path.join(root, script)), f"missing {script}"

agents = {"nova-scout.md": "haiku", "nova-reader.md": "sonnet", "nova-runner.md": "haiku"}
for name, model in agents.items():
    text = open(os.path.join(root, "agents", name), encoding="utf-8").read()
    assert f"model: {model}" in text, name

for script in ("session_start.py",):
    out = subprocess.run([sys.executable, "-I", os.path.join(root, "hooks", script)],
                         capture_output=True, text=True, check=True).stdout
    assert "<nova-dev-mode" in out or "inactive" in out or out == "", script

print("structure: all checks passed")
