"""Self-check for the next features: python -I tests/test_next.py  (exits 0 on success)."""
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
work = tempfile.mkdtemp(prefix="nd-next-")

import runtests  # noqa: E402
import tests_gate  # noqa: E402
from restore import restore_text  # noqa: E402

# 1. test detection: npm first, then pytest or unittest for Python projects, else nothing
npm = os.path.join(work, "npm")
os.makedirs(npm)
with open(os.path.join(npm, "package.json"), "w", encoding="utf-8") as fh:
    fh.write('{"scripts": {"test": "vitest"}}')
assert runtests.detect(npm) == ["npm", "test"]
py = os.path.join(work, "py")
os.makedirs(os.path.join(py, "tests"))
assert runtests.detect(py)[1:3] in (["-m", "pytest"], ["-m", "unittest"])
os.makedirs(os.path.join(work, "empty"))
assert runtests.detect(os.path.join(work, "empty")) is None

# 2. the gate reads the runner's explicit marker: pass and fail both ways
log = os.path.join(work, "gate", ".claude")
os.makedirs(log)
os.makedirs(os.path.join(work, "gate", ".git"))  # the gate only looks inside a git repo
path = os.path.join(log, "last_test_output.txt")
with open(path, "w", encoding="utf-8") as fh:
    fh.write("1 failed\nnova-dev: RESULT fail\n")
assert tests_gate.status(os.path.join(work, "gate")) == "fail"
with open(path, "w", encoding="utf-8") as fh:
    fh.write("3 failed earlier\nnova-dev: RESULT pass\n")
assert tests_gate.status(os.path.join(work, "gate")) == "pass"  # the marker wins over old text

# 3. runner: a passing command writes RESULT pass and returns 0; a failing one, fail and nonzero
code, text = runtests.run([sys.executable, "-c", "print('ok')"], work)
assert code == 0 and text.rstrip().endswith("nova-dev: RESULT pass"), text
code, text = runtests.run([sys.executable, "-c", "import sys; sys.exit(3)"], work)
assert code == 3 and text.rstrip().endswith("nova-dev: RESULT fail"), text

# 4. restore: after /clear the fresh handoff comes back, stale or missing ones do not
proj = os.path.join(work, "proj")
os.makedirs(os.path.join(proj, ".claude"))
handoff = os.path.join(proj, ".claude", "HANDOFF.md")
with open(handoff, "w", encoding="utf-8") as fh:
    fh.write("Goal: finish the parser\n")
assert "finish the parser" in restore_text({"source": "clear", "cwd": proj})
assert restore_text({"source": "startup", "cwd": proj}) == ""
old = time.time() - 3 * 24 * 3600
os.utime(handoff, (old, old))
assert restore_text({"source": "clear", "cwd": proj}) == ""
assert restore_text({"source": "clear", "cwd": os.path.join(work, "none")}) == ""

shutil.rmtree(work, ignore_errors=True)
print("next features: all checks passed")
