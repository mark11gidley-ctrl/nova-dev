"""nova-dev: one command for the tools.

Usage: python -I scripts/nd.py <command> [args]

  status                 current level and settings (secrets hidden)
  doctor                 check the install
  stats [days] [--top N] [--by-project]     measured token use
  hogs <transcript>      tool output by size, files read repeatedly
  context <transcript>   context size per turn, with jumps
  debt [root] [word]     deferred shortcuts ledger
  callers <symbol>       every use of a symbol
  outline <file>         definitions and headings with line numbers
  logs <file>            shrink a log to failing lines and tail
  secrets                scan the staged (or working) diff for secrets
  review [base]          compressed diff + secrets + test check
  seccheck               audit the plugin's own code for dangerous calls
  test [command]         run the project tests and save the result for the Stop gate
  annotate <path>        list functions that need an explanation (the annotate skill writes them)
  testcheck              logic added without a test
  find <words>           search your past prompts
  band <import|last|board|show|export>
  init [root] [level]    per-project setup
  notes <todo|docparams|stale-notes|header-check|note-density>
  git <branch-name|split-plan|conflicts|stashes|behind|pr-size|undo-preview>
  quality <dead-code|duplicates|complexity|naming|import-cycles|long-lines|magic-numbers|unused-imports>
  tests <gen-test|flaky|coverage-gap|test-names|assert-free|slow-tests>
  ctx <always-on-size|forecast|cache-breaks|big-files>
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(HERE, "..", "hooks")
sys.path.insert(0, HOOKS)

SCRIPTS = {
    "doctor": "doctor.py", "stats": "stats.py", "hogs": "toolcost.py", "context": "contexthist.py",
    "debt": "debt.py", "callers": "callers.py", "outline": "outline.py", "logs": "logsum.py",
    "secrets": "secret_scan.py", "review": "review.py", "testcheck": "testcheck.py", "find": "find_session.py",
    "band": "band.py", "init": "init.py", "seccheck": "seccheck.py", "test": "runtests.py",
    "annotate": "annotate_targets.py",
}


GROUPS = {
    "notes": "tools_notes.py",      # todo, docparams, stale-notes, header-check, note-density
    "git": "tools_git.py",          # branch-name, split-plan, conflicts, stashes, behind, pr-size, undo-preview
    "quality": "tools_quality.py",  # dead-code, duplicates, complexity, naming, import-cycles, long-lines, magic-numbers, unused-imports
    "tests": "tools_tests.py",      # gen-test, flaky, coverage-gap, test-names, assert-free, slow-tests
    "ctx": "tools_ctx.py",          # always-on-size, forecast, cache-breaks, big-files
}


def run(script, args, stdin=None):
    return subprocess.call([sys.executable, "-I", os.path.join(HERE, script)] + args, stdin=stdin)


def status_text():
    from settings import summary
    from state import get_level
    return f"level (this folder): {get_level(os.getcwd())}\n{summary()}"


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "status":
        print(status_text())
        return 0
    if cmd == "secrets":
        if subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True).returncode != 0:
            diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout
        else:
            diff = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True).stdout
        return _secrets(diff)
    if cmd in GROUPS:  # grouped tools: nd.py <group> <name> [args]
        return run(GROUPS[cmd], args)
    if cmd in SCRIPTS:
        return run(SCRIPTS[cmd], args)
    print(f"unknown command: {cmd}\n")
    print(__doc__)
    return 2


def _secrets(diff):
    sys.path.insert(0, HERE)
    from secret_scan import scan
    found = scan(diff)
    if not found:
        print("no secrets found in added lines")
        return 0
    for path, number, kind in found:
        print(f"{path}:{number}  {kind} (value hidden)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
