"""Check the install: Python, hook scripts, manifest, skills, agents, and the state folder.

Usage: python -I scripts/doctor.py   Exit 0 when everything is OK, 1 otherwise.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable


def check(label, ok, detail=""):
    print(f"[{'ok' if ok else 'FAIL'}] {label}{(': ' + detail) if detail and not ok else ''}")
    return ok


def main():
    results = []
    results.append(check("Python 3.9 or newer", sys.version_info >= (3, 9), sys.version.split()[0]))
    try:
        manifest = json.load(open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8"))
        results.append(check("plugin.json parses", manifest.get("name") == "nova-dev"))
    except (OSError, ValueError) as exc:
        results.append(check("plugin.json parses", False, str(exc)))
    hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]
    for event, groups in hooks.items():
        for group in groups:
            for h in group["hooks"]:
                m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"", h["command"])
                script = os.path.join(ROOT, m.group(1))
                results.append(check(f"{event} hook script exists", os.path.isfile(script), script))
    import shutil
    launcher = shutil.which("python") or shutil.which("py")
    results.append(check("a Python launcher is on PATH (python or py -3)", launcher is not None,
                         "install Python 3 and turn on PATH, or the hooks will not run"))
    for name in ("nova-scout.md", "nova-reader.md", "nova-runner.md"):
        results.append(check(f"agent {name}", os.path.isfile(os.path.join(ROOT, "agents", name))))
    skills = [d for d in os.listdir(os.path.join(ROOT, "skills")) if d.startswith("nova-dev")]
    results.append(check("skills present", len(skills) >= 8, f"found {len(skills)}"))
    from state import state_dir
    try:
        os.makedirs(state_dir(), exist_ok=True)
        probe = os.path.join(state_dir(), ".write-test")
        open(probe, "w").close()
        os.remove(probe)
        results.append(check("state folder writable", True))
    except OSError as exc:
        results.append(check("state folder writable", False, str(exc)))
    print(f"\n{sum(results)}/{len(results)} checks OK. Statusline is set in Claude Code settings, not checked here.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "hooks"))
    sys.exit(main())
