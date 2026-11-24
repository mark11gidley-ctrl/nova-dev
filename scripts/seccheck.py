"""Self-audit: scan nova-dev's own Python for dangerous calls and insecure URLs.

Usage: python -I scripts/seccheck.py     Exit 0 when clean, 1 when a finding needs review.
Each rule names the risk. A reviewed, justified use can be listed in ALLOW (path, rule).
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RULES = [
    ("shell=True", re.compile(r"shell\s*=\s*True"), "command injection if any part comes from input"),
    ("os.system", re.compile(r"\bos\.system\("), "shell command built as a string"),
    ("eval/exec", re.compile(r"(?<![\w.])(eval|exec)\("), "runs arbitrary code"),
    ("pickle", re.compile(r"\bpickle\.(loads?|Unpickler)\b"), "unpickling untrusted data runs code"),
    ("unsafe yaml", re.compile(r"yaml\.load\((?!.*Loader)"), "yaml.load without a safe loader runs code"),
    ("TLS off", re.compile(r"verify\s*=\s*False|CERT_NONE|_create_unverified_context"), "disables certificate checks"),
    ("plain http URL", re.compile(r"[\"']http://(?!localhost|127\.0\.0\.1)"), "sends data unencrypted"),
    ("hardcoded token", re.compile(r"(?i)(token|secret|password)\s*=\s*[\"'][^\"']{8,}[\"']"),
     "credential in source"),
]
ALLOW = {
    # (relative path, rule name): reason. Keep this list short and justified.
    ("scripts/seccheck.py", "eval/exec"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "plain http URL"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "TLS off"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "shell=True"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "os.system"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "pickle"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "unsafe yaml"): "this file names the patterns it looks for",
    ("scripts/seccheck.py", "hardcoded token"): "this file names the patterns it looks for",
    ("tests/test_band.py", "plain http URL"): "test asserts that an http webhook is refused",
    ("tests/test_report.py", "plain http URL"): "test asserts that the report has no external links",
    ("tests/test_sweep.py", "plain http URL"): "test asserts that the report has no external links",
    ("tests/test_session.py", "plain http URL"): "test asserts that the page has no external links",
    ("tests/test_security.py", "eval/exec"): "test strings name the patterns",
    ("tests/test_security.py", "plain http URL"): "test strings name the patterns",
    ("tests/test_security.py", "hardcoded token"): "test strings name the patterns",
}
SKIP_DIRS = {"__pycache__", ".git"}


def scan(root=ROOT):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for number, line in enumerate(fh, 1):
                    for rule, pattern, why in RULES:
                        if pattern.search(line) and (rel, rule) not in ALLOW:
                            findings.append((rel, number, rule, why))
    return findings


if __name__ == "__main__":
    found = scan()
    for rel, number, rule, why in found:
        print(f"{rel}:{number}  {rule}: {why}")
    print(f"{len(found)} finding(s)")
    sys.exit(1 if found else 0)
