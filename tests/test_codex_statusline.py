"""Self-check for the Codex status line: python -I tests/test_codex_statusline.py  (exits 0 on success)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "codex_statusline.py")
work = tempfile.mkdtemp(prefix="nd-cxsl-")
os.environ["NOVA_DEV_DIR"] = os.path.join(work, "state")
os.environ.pop("NOVA_DEV_PRICE_INPUT", None)
sys.path.insert(0, os.path.dirname(HOOK))

import codex_statusline as C  # noqa: E402
from savings import record  # noqa: E402

COLORS = {"primary", "surface", "accent", "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"}


def nodes(tree):
    yield tree
    for child in tree.get("children", []):
        if isinstance(child, dict):
            yield from nodes(child)


state = {"thread": {"model": {"display_name": "GPT-6.1"}, "workspace": {"cwd": os.path.join(work, "proj")},
                    "usage": {"context": {"used_percentage": 42, "used_tokens": 84000, "context_window_size": 200000},
                              "total": {"total_input_tokens": 120000, "output_tokens": 9000},
                              "cost": {"total_cost_usd": 0.37}}},
         "account": {"rate_limits": [{"primary_limit": {"used_percent": 12, "window_minutes": 300}}]}}
os.makedirs(os.path.join(work, "proj", ".git"))
os.makedirs(os.path.join(work, "proj", ".claude"))
with open(os.path.join(work, "proj", ".claude", "last_test_output.txt"), "w", encoding="utf-8") as fh:
    fh.write("3 passed, 1 failed\nnova-dev: RESULT fail\n")
record("read", 4000)
os.environ["NOVA_DEV_PRICE_INPUT"] = "3"

tree = C.render(state)
assert tree["type"] == "row"
texts = [t for n in nodes(tree) if n.get("type") == "text" for t in n.get("children", []) if isinstance(t, str)]
joined = " | ".join(texts)
for want in ("nova", "tests 3", "GPT-6.1", "ctx 42%", "5h 12%", "$0.37", "saved ~1k tok", "1 repeats"):
    assert any(want in t for t in texts), (want, joined)

# Codex limits: a node count and a size that the protocol allows (256 nodes, 16 KiB of text, depth 16)
all_nodes = list(nodes(tree))
assert len(all_nodes) <= 256, len(all_nodes)
assert len(json.dumps(tree)) < 16 * 1024
for n in all_nodes:
    if n.get("type") == "text" and "props" in n and "color" in n["props"]:
        assert n["props"]["color"] in COLORS, n["props"]["color"]

# missing pieces are skipped, never an error
bare = C.render({})
assert bare["type"] == "row" and any("nova" in t for n in nodes(bare) for t in n.get("children", []) if isinstance(t, str))

# the server speaks the protocol: initialize, list, read, unknown method
def call(messages):
    out = subprocess.run([sys.executable, "-I", HOOK], input="\n".join(json.dumps(m) for m in messages) + "\n",
                         capture_output=True, text=True, timeout=60, env=dict(os.environ))
    return [json.loads(line) for line in out.stdout.splitlines() if line.strip()]

replies = call([
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": C.URI, "_meta": {C.STATE_FIELD: state}}},
    {"jsonrpc": "2.0", "id": 4, "method": "no/such"},
    {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "ui://other"}},
])
assert replies[0]["result"]["serverInfo"]["name"] == "nova-statusline"
entry = replies[1]["result"]["tools"][0]["_meta"]["openai/ui"]["entrypoints"][0]
assert entry == {"type": "statusline", "resourceUri": C.URI}, entry
read = replies[2]["result"]["contents"][0]
assert read["mimeType"] == "application/json" and json.loads(read["text"])["type"] == "row"
assert replies[3]["error"]["code"] == -32601
assert replies[4]["error"]["code"] == -32602

shutil.rmtree(work, ignore_errors=True)
print("codex status line: all checks passed")
