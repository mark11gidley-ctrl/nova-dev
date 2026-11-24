"""The one definition of token usage. Ledger, stats, context history and the tools all use this.

Rule: a streamed message can appear several times with the same message id; the last record wins
and keeps its first position. Only complete lines count, so a line being written right now waits."""
import json

FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def usage_tuple(u):
    """(input, output, cache_read, cache_create) for one usage record."""
    return tuple((u.get(k, 0) or 0) for k in FIELDS)


def _take(raw, usage):
    """Parse one line into usage. Returns False when the line is not complete JSON."""
    try:
        rec = json.loads(raw.decode("utf-8", errors="ignore"))
    except ValueError:
        return False
    if not isinstance(rec, dict):
        return False
    msg = rec.get("message") or {}
    u = msg.get("usage")
    if rec.get("type") != "assistant" or not u:
        return True
    key = msg.get("id") or rec.get("uuid") or str(len(usage))
    usage.pop(key, None)
    usage[key] = (rec.get("timestamp", ""), usage_tuple(u))
    return True


def read_usage(path, usage=None, offset=0):
    """Read a transcript from byte `offset`. Returns (usage, new_offset).

    usage maps message key -> (timestamp, (input, output, cache_read, cache_create)).
    Pass the usage and offset from an earlier call to read only what was appended since."""
    usage = {} if usage is None else usage
    with open(path, "rb") as fh:
        fh.seek(offset)
        data = fh.read()
    end = data.rfind(b"\n")
    body, tail = (data[:end + 1], data[end + 1:]) if end >= 0 else (b"", data)
    for raw in body.split(b"\n"):
        if raw:
            _take(raw, usage)
    consumed = offset + len(body)
    if tail.strip() and _take(tail, usage):  # a last line with no newline, but complete
        consumed = offset + len(data)
    return usage, consumed


def sum_totals(tuples):
    """Totals over usage tuples: input, output, cache_read, cache_create, and the turn count."""
    t = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "turns": 0}
    for i, o, r, c in tuples:
        t["input"] += i
        t["output"] += o
        t["cache_read"] += r
        t["cache_create"] += c
        t["turns"] += 1
    return t


def context_size(tuple_):
    """Prompt size of one turn: fresh input plus both kinds of cached input."""
    i, _o, r, c = tuple_
    return i + r + c
