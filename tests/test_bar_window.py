"""Self-check for the desktop bar window's text: python -I tests/test_bar_window.py  (exits 0 on success)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "hooks"))
import bar_window as B  # noqa: E402

rows = dict(B.lines_for({
    "level": "full", "project": "nova-dev", "tests_counts": {"passed": 40, "failed": 1},
    "session": {"agent_ms": 90_000, "input": 1000, "cache_read": 0, "cache_create": 0, "output": 5000,
                "turns": 3, "context": 50_000},
    "summary": {"tokens7": 2_000_000, "limit_pct": 30, "saved_tokens": 4000, "saved_cost": 0.012, "saved_reads": 2},
}))
assert "FULL" in rows["head"] and "40 passed" in rows["head"] and "1 failing" in rows["head"], rows
assert "1m 30s" in rows["session"] and "3 turns" in rows["session"], rows
assert "30%" in rows["limit"], rows
assert "$0.01" in rows["saved"] and "2 repeats" in rows["saved"], rows
# missing data leaves lines out instead of failing
bare = dict(B.lines_for({}))
assert list(bare) == ["head"] and "UNSET" in bare["head"], bare
print("bar window: all checks passed")
