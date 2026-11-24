// Cross-shell launcher for nova-dev's Python hooks (used by the Codex hook file).
// Run through: node -e "require(...launch.js)" <hook.py> [args]. Tries the Windows launcher, then python.
const { spawnSync } = require("child_process");
const path = require("path");
const script = path.join(__dirname, process.argv[1]);
const extra = process.argv.slice(2);
for (const [cmd, pre] of [["py", ["-3"]], ["python", []], ["python3", []]]) {
  const r = spawnSync(cmd, [...pre, "-I", script, ...extra], { stdio: "inherit" });
  if (!r.error) process.exit(r.status === null ? 1 : r.status);
}
console.error("nova-dev: no Python 3 found on PATH (install Python or the py launcher)");
process.exit(1);
