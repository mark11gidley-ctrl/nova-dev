"""Set up nova-dev in a project: a per-project config, and git ignores for generated files.

Usage: python -I scripts/init.py [project_root] [level]   level is chosen by the user: off, lite, full or ultra.
Without a level, no config is written.
Never overwrites an existing config. Prints every action it took.
"""
import json
import os
import sys

IGNORES = [".claude/CONTEXT-SNAPSHOT.md", ".claude/last_test_output.txt"]


def init(root, level=None):
    actions = []
    cfg_dir = os.path.join(root, ".claude")
    cfg = os.path.join(cfg_dir, "nova-dev.json")
    if level is not None and level not in ("off", "lite", "full", "ultra"):
        raise ValueError("level must be off, lite, full or ultra")
    if os.path.exists(cfg):
        actions.append("kept existing .claude/nova-dev.json")
    elif level is None:
        actions.append("no level given: .claude/nova-dev.json not written; choose off, lite, full or ultra")
    else:
        os.makedirs(cfg_dir, exist_ok=True)
        with open(cfg, "w", encoding="utf-8") as fh:
            json.dump({"level": level}, fh, indent=2)
        actions.append(f"wrote .claude/nova-dev.json (level {level})")
    gi = os.path.join(root, ".gitignore")
    if os.path.isdir(os.path.join(root, ".git")):
        text = ""
        if os.path.exists(gi):
            with open(gi, encoding="utf-8") as fh:
                text = fh.read()
        existing = text.splitlines()
        missing = [line for line in IGNORES if line not in existing]
        if missing:
            # start on a fresh line if the file does not end with one, or the first entry joins the last line
            lead = "\n" if text and not text.endswith("\n") else ""
            with open(gi, "a", encoding="utf-8") as fh:
                fh.write(lead + "\n".join(missing) + "\n")
            actions.append(f"added to .gitignore: {', '.join(missing)}")
        else:
            actions.append(".gitignore already covers generated files")
    else:
        actions.append("not a git repository: .gitignore left alone")
    return actions


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    level = sys.argv[2] if len(sys.argv) > 2 else None
    for action in init(root, level):
        print(action)
    sys.exit(0)
