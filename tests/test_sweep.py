"""Whole-plugin sweep: python -I tests/test_sweep.py  (exits 0 on success).

Checks what the per-module tests do not: every JSON file parses, every skill has valid frontmatter, every
hook runs without a traceback on sample input, every CLI entry point is reachable, and the status outputs
work. All state goes to a temporary folder, so your real settings and data are never touched."""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
HOOKS = os.path.join(ROOT, "hooks")
work = tempfile.mkdtemp(prefix="nd-sweep-")
env = dict(os.environ, NOVA_DEV_DIR=os.path.join(work, "state"), CLAUDE_CONFIG_DIR=os.path.join(work, "claude"))
sample_file = os.path.join(work, "sample.py")
open(sample_file, "w", encoding="utf-8").write("x = 1\n")
failures = []


def check(label, ok, detail=""):
    if not ok:
        failures.append(f"{label}: {detail}")


def run(argv, stdin=""):
    return subprocess.run([sys.executable, "-I"] + argv, input=stdin, capture_output=True, text=True,
                          env=env, timeout=300)


# 1. every JSON file in the plugin parses
for path in glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True):
    if "__pycache__" in path:
        continue
    try:
        json.load(open(path, encoding="utf-8"))
    except ValueError as exc:
        check("json", False, f"{os.path.relpath(path, ROOT)}: {exc}")

# 2. every skill: the frontmatter name matches its folder, and there is a description
for skill in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")):
    text = open(skill, encoding="utf-8").read()
    folder = os.path.basename(os.path.dirname(skill))
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    check("skill frontmatter", bool(m), folder)
    if m:
        check("skill name", re.search(rf"^name: {re.escape(folder)}$", m.group(1), re.M) is not None, folder)
        check("skill description", re.search(r"^description: .+", m.group(1), re.M) is not None, folder)

# 3. every hook: the script exists, and runs on sample input without a traceback
hooks = json.load(open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8"))["hooks"]
payload = json.dumps({"session_id": "sweep", "cwd": work, "prompt": "hello there", "source": "startup",
                      "transcript_path": "", "tool_input": {"file_path": sample_file, "command": "git status"}})
for event, groups in hooks.items():
    for group in groups:
        for h in group["hooks"]:
            script = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"", h["command"]).group(1)
            path = os.path.join(ROOT, script)
            check("hook script exists", os.path.isfile(path), script)
            first = h["command"].split(" ||")[0]  # the first launcher: its arguments follow the script path
            args = first.split('\"')[-1].split()  # for example: ["pre"], ["bash"], [] 
            for stdin in (payload, ""):  # sample input, then empty input (a hook must survive either)
                r = subprocess.run([sys.executable, "-I", path] + args, input=stdin, capture_output=True, text=True,
                                   env=env, timeout=120)
                check(f"hook {script} exit", r.returncode in (0, 2), f"exit {r.returncode}: {r.stderr[-200:]}")
                check(f"hook {script} traceback", "Traceback" not in r.stderr, r.stderr[-300:])

# 4. every CLI entry point: its script exists, and it runs without a traceback
sys.path.insert(0, SCRIPTS)
nd_src = open(os.path.join(SCRIPTS, "nd.py"), encoding="utf-8").read()
for name in re.findall(r'"([\w-]+)": "([\w.]+\.py)"', nd_src):
    check("nd.py target exists", os.path.isfile(os.path.join(SCRIPTS, name[1])), name[1])
for group, target in re.findall(r'"([\w-]+)": "(tools_\w+\.py|game_tools\.py|video_tools\.py)"', nd_src):
    r = run([os.path.join(SCRIPTS, target)])
    check(f"group {group} runs", "Traceback" not in r.stderr and r.returncode in (0, 2), r.stderr[-300:])
for name in ("doctor.py", "seccheck.py", "report.py", "setup.py"):
    r = run([os.path.join(SCRIPTS, name)])
    check(f"{name} runs", "Traceback" not in r.stderr, r.stderr[-300:])
for cmd in ("status", "version", "config", "help"):
    r = run([os.path.join(SCRIPTS, "nd.py"), cmd])
    check(f"nd.py {cmd}", r.returncode == 0 and "Traceback" not in r.stderr, r.stderr[-300:])
r = run([os.path.join(SCRIPTS, "nd.py"), "versoin"])
check("typo suggestion", r.returncode == 2 and "version" in r.stdout, r.stdout)

# 5. the status outputs
r = run([os.path.join(HOOKS, "statusline.py"), "--band", work])
check("band text", r.returncode == 0 and "nova-dev" in r.stdout, r.stderr[-200:])
r = run([os.path.join(HOOKS, "statusline.py"), "--band-json", work])
check("band json", r.returncode == 0 and json.loads(r.stdout).get("level") is not None, r.stderr[-200:])

# 6. the bar module: it reads the JSON output, and its brackets balance
bar = open(os.path.join(HOOKS, "band", "register.tsx"), encoding="utf-8").read()
check("bar uses band json", "--band-json" in bar)
check("bar brackets balance", all(bar.count(a) == bar.count(b) for a, b in (("(", ")"), ("{", "}"), ("[", "]"))))
check("bar caches", "CACHE_MS" in bar and "$.store.get" in bar)

# 7. the HTML report builds with no external references
r = run([os.path.join(SCRIPTS, "report.py"), os.path.join(work, "r.html")])
page = open(os.path.join(work, "r.html"), encoding="utf-8").read() if r.returncode == 0 else ""
check("report builds", r.returncode == 0 and "<html" in page, r.stderr[-200:])
check("report has no external links", "http://" not in page and "https://" not in page)

shutil.rmtree(work, ignore_errors=True)
if failures:
    print("sweep found problems:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("plugin sweep: all checks passed")
