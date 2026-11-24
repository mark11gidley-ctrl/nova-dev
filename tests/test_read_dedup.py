"""Self-check: python -I tests/test_read_dedup.py  (exits 0 on success)."""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
from read_dedup import cache_file, decide  # noqa: E402

work = tempfile.mkdtemp(prefix="tl-test-")
cdir = os.path.join(work, "cache")
os.makedirs(cdir)
f = os.path.join(work, "a.txt")
with open(f, "w") as fh:
    fh.write("hello")

sid = f"test-{time.time_ns()}"
full = {"session_id": sid, "tool_input": {"file_path": f}}
part = {"session_id": sid, "tool_input": {"file_path": f, "offset": 5, "limit": 10}}

# first full read is allowed; recording it makes the next identical read blocked
assert decide("pre", full, cdir)[0] == 0
decide("post", full, cdir)
assert decide("pre", full, cdir)[0] == 2
# partial reads are never blocked
assert decide("pre", part, cdir)[0] == 0
# edited file (size changes) is allowed again
with open(f, "w") as fh:
    fh.write("hello world, changed")
assert decide("pre", full, cdir)[0] == 0
# missing file is allowed; Read reports the error itself
missing = {"session_id": sid, "tool_input": {"file_path": f + ".nope"}}
assert decide("pre", missing, cdir)[0] == 0

shutil.rmtree(work, ignore_errors=True)
print("read-dedup: all checks passed")
