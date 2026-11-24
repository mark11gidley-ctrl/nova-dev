"""Self-check: python -I tests/test_annotate.py  (exits 0 on success)."""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from annotate_targets import generic_targets, python_targets, scan  # noqa: E402

long_body = "    x = 1\n" * 9
py_src = (
    "def bare():\n" + long_body +                       # long, undocumented -> target
    "\ndef documented():\n    \"\"\"Explains why.\"\"\"\n" + long_body +   # docstring -> skip
    "\n# why: keeps the order stable\ndef commented():\n" + long_body +    # comment above -> skip
    "\ndef short():\n    return 1\n"                    # short -> skip
)
found = python_targets(py_src, 8)
assert [name for _, name, _ in found] == ["bare"], found
assert python_targets("def broken(:\n", 8) == []        # bad syntax is skipped, not crashed on

js_src = "function plain() {\n" + "  a();\n" * 9 + "}\n// explains the rule\nfunction noted() {\n" + "  a();\n" * 9 + "}\n"
found_js = generic_targets(js_src, 8)
assert [name for _, name, _ in found_js] == ["plain"], found_js

work = tempfile.mkdtemp(prefix="nd-ann-")
os.makedirs(os.path.join(work, "node_modules"))
with open(os.path.join(work, "a.py"), "w", encoding="utf-8") as fh:
    fh.write(py_src)
with open(os.path.join(work, "node_modules", "skip.py"), "w", encoding="utf-8") as fh:
    fh.write(py_src)
rows = scan(work, 8)
assert len(rows) == 1 and rows[0][2] == "bare", rows  # node_modules is skipped
shutil.rmtree(work, ignore_errors=True)
print("annotate: all checks passed")
