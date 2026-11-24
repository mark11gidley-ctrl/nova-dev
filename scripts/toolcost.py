"""Which tools fill your context: result size per tool, and files read more than once.

Usage: python -I scripts/toolcost.py <transcript.jsonl> [top]   (top defaults to 10)
Sizes are characters of tool output as recorded in the transcript (measured, not estimated).
"""
import json
import sys


def analyze(path):
    names = {}
    per_tool = {}
    reads = {}
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            if rec.get("type") == "assistant":
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        names[c.get("id")] = c.get("name", "?")
                        inp = c.get("input") or {}
                        fp = inp.get("file_path") or inp.get("path")
                        if c.get("name") == "Read" and fp:
                            reads[fp] = reads.get(fp, 0) + 1
            elif rec.get("type") == "user":
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        body = c.get("content")
                        if isinstance(body, str):
                            size = len(body)
                        elif isinstance(body, list):
                            size = sum(len(x.get("text", "")) for x in body if isinstance(x, dict))
                        else:
                            size = 0
                        name = names.get(c.get("tool_use_id"), "?")
                        calls, chars = per_tool.get(name, (0, 0))
                        per_tool[name] = (calls + 1, chars + size)
    return per_tool, {k: v for k, v in reads.items() if v > 1}


def report(per_tool, repeats, top=10):
    rows = sorted(per_tool.items(), key=lambda kv: kv[1][1], reverse=True)[:top]
    lines = ["Tool output by size (characters):"]
    lines += [f"  {chars:>12,}  {calls:>5} call(s)  {name}" for name, (calls, chars) in rows]
    if repeats:
        lines.append("Files read more than once:")
        lines += [f"  {n}x  {p}" for p, n in sorted(repeats.items(), key=lambda kv: -kv[1])[:top]]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(report(*analyze(sys.argv[1]), top=top))
    sys.exit(0)
