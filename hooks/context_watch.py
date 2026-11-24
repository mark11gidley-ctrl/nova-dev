"""Context watch: measure the current session's prompt size from its transcript and
return a one-time warning when it passes the threshold. Costs nothing when under it."""
import json
import os

from state import state_dir  # noqa: F401 (used by warn_once and autocompact_block)

DEFAULT_THRESHOLD = 150_000
TAIL_BYTES = 400_000  # the last assistant record is near the end; never read a whole transcript


AUTOCOMPACT_PERCENT = 55
AUTOCOMPACT_DEBOUNCE = 600  # seconds


def window():
    from settings import get as setting
    return setting("window")


def autocompact_block(session_id, tokens, now=None):
    """Opt-in (NOVA_DEV_AUTOCOMPACT=1): return a message that blocks the prompt once per 10 minutes
    when context passes 55% of the window. The user must type /compact; a hook cannot run it."""
    from settings import get as setting
    if not setting("autocompact") or tokens is None:
        return None
    pct = tokens * 100 // window()
    if pct < AUTOCOMPACT_PERCENT:
        return None
    import time
    flag_dir = os.path.join(state_dir(), "compact")
    os.makedirs(flag_dir, exist_ok=True)
    flag = os.path.join(flag_dir, "".join(c if c.isalnum() or c in "-_" else "_" for c in str(session_id or "none")))
    now = time.time() if now is None else now
    if os.path.exists(flag) and now - os.path.getmtime(flag) < AUTOCOMPACT_DEBOUNCE:
        return None
    open(flag, "w").close()
    return (f"Context is at {pct}% of the window. Prompt paused: type /compact, then send your message again "
            "(optionally summarize the task state first).")


def threshold():
    from settings import get as setting
    return setting("context_warn")


def current_context_tokens(transcript_path):
    """Prompt size of the latest assistant turn: fresh input plus cached input."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return None
    with open(transcript_path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - TAIL_BYTES))
        tail = fh.read().decode("utf-8", errors="ignore").splitlines()
    for line in reversed(tail):
        try:
            usage = (json.loads(line).get("message") or {}).get("usage")
        except ValueError:
            continue
        if usage:
            return (usage.get("input_tokens", 0) or 0) \
                + (usage.get("cache_read_input_tokens", 0) or 0) \
                + (usage.get("cache_creation_input_tokens", 0) or 0)
    return None


def warn_once(session_id, tokens, limit=None):
    """Return a warning the first time this session crosses the threshold, else None."""
    limit = threshold() if limit is None else limit
    if tokens is None or tokens < limit:
        return None
    flag_dir = os.path.join(state_dir(), "warned")
    os.makedirs(flag_dir, exist_ok=True)
    flag = os.path.join(flag_dir, "".join(c if c.isalnum() or c in "-_" else "_" for c in str(session_id or "none")))
    if os.path.exists(flag):
        return None
    open(flag, "w").close()
    return (f"nova-dev: this session's context is about {tokens:,} tokens (warning at {limit:,}). "
            "Tell the user now: suggest /compact, or starting a new session for the next task, "
            "because every turn re-reads the whole context.")
