"""Self-check: python -I tests/test_state_and_prompt.py  (exits 0 on success)."""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
os.environ["NOVA_DEV_DIR"] = tempfile.mkdtemp(prefix="nd-state-")

from state import get_level, set_level  # noqa: E402
from prompt_submit import decide  # noqa: E402

assert get_level() == "unset"                     # no default: the user chooses
assert decide("/nova-dev lite") == "Nova dev level is now lite."
assert get_level() == "lite"                      # persisted
assert decide("nova dev ultra") == "Nova dev level is now ultra."
assert decide("/NOVA-DEV OFF") == "Nova dev level is now off."
assert get_level() == "off"
assert decide("stop nova dev") == "Nova dev is off. Normal mode."
set_level("full")
assert decide("normal mode") == "Nova dev is off. Normal mode."
assert decide("please review my code") is None    # ordinary prompts untouched
assert decide("nova dev is great, thanks") is None
try:
    set_level("max")
    raise AssertionError("invalid level accepted")
except ValueError:
    pass

from context_watch import current_context_tokens, warn_once  # noqa: E402

# context watch: reads the latest turn, warns once, stays quiet under the limit
tp = os.path.join(os.environ["NOVA_DEV_DIR"], "t.jsonl")
with open(tp, "w", encoding="utf-8") as fh:
    fh.write('{"message":{"usage":{"input_tokens":5,"cache_read_input_tokens":100,"cache_creation_input_tokens":20}}}\n')
    fh.write("not json\n")
assert current_context_tokens(tp) == 125
assert current_context_tokens(os.path.join(os.environ["NOVA_DEV_DIR"], "missing.jsonl")) is None
assert warn_once("s9", 125, limit=150) is None
assert "about 200 tokens" in warn_once("s9", 200, limit=150)
assert warn_once("s9", 200, limit=150) is None        # only once per session

shutil.rmtree(os.environ["NOVA_DEV_DIR"], ignore_errors=True)
print("state and prompt: all checks passed")
