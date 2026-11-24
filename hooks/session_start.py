"""SessionStart: inject the rules for the current level. Prints nothing when off."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import get_level  # noqa: E402

RULES = {
    "lite": "Build what was asked. Name the smaller option in one line and let the user pick.",
    "full": ("Write the smallest change that fully works. Check every caller, test and fixture it touches. "
             "Add one small test for new non-trivial logic. Never cut validation, security or data-loss handling. "
             "Keep raw content out of context: Grep/Glob first, Read only the needed range, never re-read a file you "
             "already have, filter verbose command output (tail, grep -c, --quiet), batch independent tool calls, "
             "and hand bulk searching or test runs to a cheap subagent when you don't need their raw output."),
    "ultra": ("Before building, push back on any part of the request the need does not justify. "
              "Then write the smallest change that fully works, with every caller, test and fixture checked."),
}

# short rules: the same obligations in one line, for users who want the smallest session prompt
SHORT = {
    "lite": "Smallest option; the user picks the rest.",
    "full": "Smallest correct change; check callers and tests; Skipped/Risk line at the end.",
    "ultra": "Push back on unneeded parts first; then the smallest correct change; Skipped/Risk line.",
}


def rules_text(level):
    from settings import get as setting
    style = setting("rules_style")
    return (SHORT if style == "short" else RULES).get(level, "")


level = get_level()
if level in RULES:
    sys.stdout.write(
        f"<nova-dev-mode level=\"{level}\">\n{rules_text(level)}\n"
        "End each reply with: Skipped: ... / Risk: ...\n</nova-dev-mode>\n"
    )
elif level == "unset":
    # nothing is active until the user chooses; say so once, not every session
    import os
    from state import state_dir
    flag = os.path.join(state_dir(), "hinted")
    if not os.path.exists(flag):
        os.makedirs(state_dir(), exist_ok=True)
        open(flag, "w").close()
        sys.stdout.write("nova-dev is installed but inactive. Choose a level: say 'nova dev lite', "
                         "'nova dev full', 'nova dev ultra' or 'nova dev off', or run nova-dev-init.\n")
sys.exit(0)
