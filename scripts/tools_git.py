"""Git workflow helpers. Usage: nd.py git <name> [args]

  branch-name <task text>   a branch name from a task: prefix by type, kebab-case, 40 characters max
  split-plan                group the working changes into commits by top-level folder (proposal only)
  conflicts [root]          files with conflict markers: hunks, and lines on each side
  stashes                   stash entries with age and the files each one touches
  behind [base]             commits the current branch is behind the base (as of the last fetch)
  pr-size [base]            lines changed against the base, with a size label and a split hint
  undo-preview              what the last commit contains, so you know what a reset would drop

Read-only: none of these change the repository. They need git on PATH.
"""
import os
import re
import subprocess
import sys

KINDS = [("fix/", r"\b(fix|bug|crash|error|broken|wrong)\b"), ("docs/", r"\b(doc|docs|readme|comment)\b"),
         ("test/", r"\b(test|tests|coverage)\b"), ("refactor/", r"\b(refactor|clean|simplify|rename)\b")]


def git(args, cwd=None):
    out = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def branch_name(text):
    prefix = next((p for p, pat in KINDS if re.search(pat, text.lower())), "feat/")
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return prefix + slug[:40].rstrip("-")


def split_plan(root):
    code, out, err = git(["status", "--porcelain"], root)
    if code != 0:
        return [f"not a git repository: {err}"]
    groups = {}
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        top = path.split("/")[0] if "/" in path else "(root)"
        groups.setdefault(top, []).append(path)
    return [f"commit {i}: {top} ({len(files)} file{'s' if len(files) != 1 else ''})"
            for i, (top, files) in enumerate(sorted(groups.items()), 1)]


def conflicts(root):
    code, out, _ = git(["diff", "--name-only", "--diff-filter=U"], root)
    rows = []
    for path in out.splitlines():
        try:
            text = open(os.path.join(root, path), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        hunks = len(re.findall(r"^<<<<<<< ", text, re.M))
        ours = len(re.findall(r"^<<<<<<< .*\n(.*?)^=======", text, re.M | re.S))
        rows.append(f"{path}: {hunks} conflict hunk(s)")
        if hunks:
            blocks = re.findall(r"^<<<<<<< .*?\n(.*?)^=======\n(.*?)^>>>>>>> ", text, re.M | re.S)
            for n, (mine, theirs) in enumerate(blocks, 1):
                rows.append(f"  hunk {n}: this side {mine.count(chr(10))} line(s), other side {theirs.count(chr(10))} line(s)")
    return rows or ["no unmerged files"]


def stashes(root):
    code, out, _ = git(["stash", "list", "--format=%gd|%cr|%s"], root)
    rows = []
    for line in out.splitlines():
        ref, age, subject = (line.split("|", 2) + ["", ""])[:3]
        _, files, _ = git(["stash", "show", "--name-only", ref], root)
        rows.append(f"{ref}  {age}  {len(files.splitlines())} file(s)  {subject}")
    return rows or ["no stashes"]


def behind(root, base=None):
    base = base or (git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)[1] or "main")
    code, out, err = git(["rev-list", "--count", f"HEAD..{base}"], root)
    if code != 0:
        return [f"cannot compare with {base}: {err}"]
    return [f"{out} commit(s) behind {base} (as of the last fetch; run git fetch first for the latest)"]


def pr_size(root, base=None):
    base = base or (git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)[1] or "main")
    code, out, err = git(["diff", "--numstat", f"{base}...HEAD"], root)
    if code != 0:
        return [f"cannot compare with {base}: {err}"]
    added = deleted = files = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] != "-":
            added += int(parts[0])
            deleted += int(parts[1])
            files += 1
    lines = added + deleted
    label = "small" if lines <= 200 else "medium" if lines <= 600 else "large"
    hint = "" if label != "large" else " -- consider splitting by folder (see split-plan)"
    return [f"{files} file(s), +{added} -{deleted} ({label}){hint}"]


def undo_preview(root):
    code, out, err = git(["show", "--stat", "--format=%h %s", "HEAD"], root)
    return out.splitlines() if code == 0 else [err]


def main(argv):
    names = {"branch-name", "split-plan", "conflicts", "stashes", "behind", "pr-size", "undo-preview"}
    if not argv or argv[0] not in names:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    cwd = os.getcwd()
    if cmd == "branch-name":
        rows = [branch_name(" ".join(rest))]
    elif cmd == "split-plan":
        rows = split_plan(cwd)
    elif cmd == "conflicts":
        rows = conflicts(cwd)
    elif cmd == "stashes":
        rows = stashes(cwd)
    elif cmd == "behind":
        rows = behind(cwd, rest[0] if rest else None)
    elif cmd == "pr-size":
        rows = pr_size(cwd, rest[0] if rest else None)
    else:
        rows = undo_preview(cwd)
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
