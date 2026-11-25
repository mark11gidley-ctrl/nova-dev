"""Secret patterns and redaction, shared by the ledger, the snapshot, the scanner and the review.
Matched values are never returned; callers only get a kind label."""
import re

MAX_LINE = 5000  # longer lines are cut before matching, which keeps the regexes fast

PATTERNS = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("assigned secret", re.compile(
        r"(?i)\b\w*(?:api[_-]?key|secret|token|password|passwd|private[_-]?key|access[_-]?key|key)\w*"
        # a real credential almost always has a digit; a plain name such as "codex-statusline-state" does not
        r"\s*[:=]\s*['\"](?=[^'\"\s]*\d)[^'\"\s]{8,}['\"]")),
]


def line_kind(body):
    body = body[:MAX_LINE]
    for kind, pattern in PATTERNS:
        if pattern.search(body):
            return kind
    return None


def redact_text(text):
    """Replace every secret-looking span with a marker. Safe to store, log or send."""
    out = text
    for kind, pattern in PATTERNS:
        out = pattern.sub(f"[hidden: {kind}]", out)
    return out
