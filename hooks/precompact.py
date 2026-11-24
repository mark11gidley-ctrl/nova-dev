"""PreCompact: save the last user/assistant turns to .claude/CONTEXT-SNAPSHOT.md before compaction."""
import json
import os
import sys

try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)

transcript = data.get("transcript_path") or ""
cwd = data.get("cwd") or os.getcwd()
if not transcript or not os.path.isfile(transcript):
    sys.exit(0)


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


entries = []
with open(transcript, encoding="utf-8") as fh:
    lines = [l.strip() for l in fh if l.strip()]
for line in lines[-150:]:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    body = msg.get("message")
    if not body:
        continue
    role = msg.get("type", "")
    content = body.get("content", "")
    if role == "user":
        t = text_of(content).strip()
        if t:
            entries.append(f"[User] {t[:400]}")
    elif role == "assistant" and isinstance(content, list):
        texts = [c["text"][:300] for c in content if c.get("type") == "text" and c.get("text")]
        tools = [f"[{c['name']}]" for c in content if c.get("type") == "tool_use"]
        summary = (" ".join(texts[:1]) + " " + " ".join(tools)).strip()
        if summary:
            entries.append(f"[Assistant] {summary}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import redact_text  # noqa: E402
output = redact_text("\n\n".join(entries))
if len(output) > 12000:
    output = "...(earlier truncated)...\n\n" + output[-12000:]

snapshot = os.path.join(cwd, ".claude", "CONTEXT-SNAPSHOT.md")
os.makedirs(os.path.dirname(snapshot), exist_ok=True)
from state import write_private  # noqa: E402
write_private(snapshot, "# Pre-Compact Context Snapshot\n\n" + output + "\n")
sys.exit(0)
