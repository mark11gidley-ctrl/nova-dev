"""Lazy-test rule as a check: a change that adds real logic should touch a test file.

Usage: python -I scripts/testcheck.py [threshold]   (default threshold: 20 added source lines)
Reads `git diff --numstat HEAD`. Exit 0 when fine, 1 when logic was added with no test touched.
"""
import re
import subprocess
import sys

TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_[^/]*$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$",
                       re.I)
SKIP_PATH = re.compile(r"\.(md|txt|lock|json|ya?ml|toml|svg|png|jpe?g)$|(^|/)(LICENSE|AGENTS\.md)$", re.I)


def analyze(numstat, threshold=20):
    """numstat: text from `git diff --numstat`. Returns (ok, source_added, test_files, message)."""
    source_added = 0
    tests = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, _deleted, path = parts
        if added == "-":  # binary
            continue
        if TEST_PATH.search(path):
            tests.append(path)
        elif not SKIP_PATH.search(path):
            source_added += int(added)
    if source_added >= threshold and not tests:
        return False, source_added, tests, (f"{source_added} source lines added and no test file changed. "
                                            "Add one small test for the new logic.")
    return True, source_added, tests, "ok"


def main(threshold):
    try:
        out = subprocess.run(["git", "diff", "--numstat", "HEAD"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"not checked: {exc}")
        return 0
    if out.returncode != 0:
        print("not checked: not a git repository or no commits yet")
        return 0
    ok, added, tests, message = analyze(out.stdout, threshold)
    print(f"source lines added: {added}; test files changed: {len(tests)}; {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    sys.exit(main(limit))
