"""Write nova-dev's rules into each agent's rule file format.

Usage: python -I scripts/build_adapters.py <target folder>
Source: rules/core.md. Output files are regenerated every run; edit core.md, not the outputs.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(HERE, "..", "rules", "core.md")

TARGETS = {
    "AGENTS.md": "{core}",  # Codex, OpenCode, Gemini, Antigravity, and any AGENTS.md reader
    ".cursor/rules/nova-dev.mdc": "---\ndescription: Nova Dev lazy developer rules\nalwaysApply: true\n---\n\n{core}",
    ".windsurf/rules/nova-dev.md": "---\ntrigger: always_on\n---\n\n{core}",
    ".clinerules/nova-dev.md": "{core}",
    ".github/copilot-instructions.md": "{core}",
    ".kiro/steering/nova-dev.md": "---\ninclusion: always\n---\n\n{core}",
    ".qoder/rules/nova-dev.md": "{core}",
}


def build(target_root):
    with open(CORE, encoding="utf-8") as fh:
        core = fh.read().strip()
    written = []
    for rel, template in TARGETS.items():
        path = os.path.join(target_root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(template.format(core=core) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    for path in build(root):
        print(path)
    sys.exit(0)
