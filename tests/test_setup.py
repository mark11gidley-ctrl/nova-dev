"""Self-check for setup: python -I tests/test_setup.py  (exits 0 on success). Never installs anything."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import setup as S  # noqa: E402

# nothing on PATH and no known install folders: every item is missing, and required ones are flagged
real_known = S._known
S._known = lambda name: False
none_found = S.missing(which=lambda name: None)
names = [n for n, _, _ in none_found]
assert "Git" in names and "ffmpeg (video tools)" in names, names
assert any(req for n, _, req in none_found if n == "Git") and not any(req for n, _, req in none_found if n.startswith("ffmpeg"))

S._known = real_known
# everything on PATH: nothing missing
all_found = S.missing(which=lambda name: "/fake/" + name)
assert all_found == [], all_found

# install calls the resolved program, not the bare name
calls = []
ok = S.install(["npm", "install", "-g", "x"], runner=lambda argv, check: calls.append(argv) or type("R", (), {"returncode": 0})(),
               which=lambda name: "C:/tools/npm.cmd")
assert ok and calls[0][0] == "C:/tools/npm.cmd", calls

# without --yes and without a terminal, the script installs nothing
import io
old_stdin = sys.stdin
sys.stdin = io.StringIO("")
try:
    assert S.main([]) in (0,)
finally:
    sys.stdin = old_stdin
print("setup: all checks passed")
