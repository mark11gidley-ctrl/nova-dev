---
name: nova-dev-init
description: Set up nova-dev in a project. Asks the user which level to use (off, lite, full or ultra), writes a per-project level file, and adds git ignores for generated files. Never overwrites an existing config. Use for "nova dev init" in a new project.
---

# Nova Dev Init

nova-dev has no default level. Until the user chooses one, nothing is active.

1. Ask the user which level to use, with AskUserQuestion, and explain each choice:
   - **lite:** build what was asked; name the smaller option and let the user pick.
   - **full:** the complete rules: smallest change, every caller checked, one test for new logic.
   - **ultra:** like full, and push back on any part of a request the need does not justify.
   - **off:** nothing active in this project.
2. Run from the project root with the chosen level:

```
python -I "${CLAUDE_PLUGIN_ROOT}/scripts/init.py" . <level>
```

3. Report each action the script prints.
4. If the project should also get rule files for other agents, ask first, then run `python -I "${CLAUDE_PLUGIN_ROOT}/scripts/build_adapters.py" .` and list the files written.

Do not commit anything. The user can change the level later with `nova dev <level>`, or edit `.claude/nova-dev.json`.
