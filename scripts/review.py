"""One-shot review bundle: compressed diff, secrets scan, and the test check, in one report.

Usage: python -I scripts/review.py [base]   (base defaults to HEAD; the working tree is compared)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from diffcompress import compress  # noqa: E402
from secret_scan import redact, scan as secret_scan  # noqa: E402
from testcheck import analyze  # noqa: E402


def git(args):
    out = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=60)
    return out.returncode, out.stdout


def bundle(diff_text, numstat_text, threshold=20, cap=80):
    lines = ["## Diff (compressed)"]
    lines += redact(compress(diff_text, cap)) or ["(no changes)"]
    findings = secret_scan(diff_text)
    lines.append("## Secrets")
    lines += [f"{p}:{n}  {k} (value hidden)" for p, n, k in findings] or ["none in added lines"]
    ok, added, tests, message = analyze(numstat_text, threshold)
    lines.append("## Tests")
    lines.append(f"source lines added: {added}; test files changed: {len(tests)}; {message}")
    lines.append("## Verdict")
    lines.append("clean" if ok and not findings else "needs attention: see Secrets or Tests above")
    return "\n".join(lines)


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    code, diff = git(["diff", base])
    code2, numstat = git(["diff", "--numstat", base])
    if code != 0 or code2 != 0:
        print("not a git repository, or no commits yet: nothing to review")
        sys.exit(0)
    print(bundle(diff, numstat))
    sys.exit(0)
