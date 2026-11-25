"""Codex status line for Nova Dev: one row with level, tests, model, context, limits, tokens, cost, and savings.

Codex starts this as an MCP server over stdio (newline-delimited JSON-RPC). Register it once:
    codex mcp add nova-statusline -- py -3 -u "C:/path/to/nova-dev/hooks/codex_statusline.py"
Then start a new Codex thread, open /statusline and choose the provider.

Codex sends the thread's state with each read: model, context use, token totals, cost and rate limits.
Nova Dev adds what only it knows: the level, the last test result, and what the guards saved."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

URI = "ui://nova-dev/footer"
TOOL = {
    "name": "statusline",
    "title": "Nova Dev",
    "description": "Show Nova Dev's level, tests, context, limits, tokens, cost and savings in the Codex footer.",
    "inputSchema": {"type": "object", "properties": {}},
    "_meta": {"openai/ui": {"entrypoints": [{"type": "statusline", "resourceUri": URI}]}},
}
STATE_FIELD = "com.openai/codex-statusline-state"


def fmt(n):
    n = float(n or 0)
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else f"{int(n)}"


def pct_color(pct):
    return "green" if pct < 50 else "yellow" if pct < 75 else "red"


def nova_facts(cwd):
    """What Nova Dev knows: level, last test result, savings and their money value. Never raises."""
    facts = {"level": "unset", "tests": None, "saved_tokens": 0, "saved_reads": 0, "saved_cost": None}
    try:
        from state import get_level
        facts["level"] = get_level(cwd)
    except Exception:
        pass
    try:
        from tests_gate import counts
        facts["tests"] = counts(cwd)
    except Exception:
        pass
    try:
        from savings import load
        from settings import get as setting
        read = load().get("read", {"count": 0, "bytes": 0})
        facts["saved_reads"] = int(read["count"])
        facts["saved_tokens"] = int(read["bytes"]) // 4
        price = float(setting("price_input"))
        facts["saved_cost"] = facts["saved_tokens"] * price / 1_000_000 if price else None
    except Exception:
        pass
    return facts


def text(value, color=None, weight=None):
    props = {}
    if color:
        props["color"] = color
    if weight:
        props["weight"] = weight
    node = {"type": "text", "children": [value]}
    if props:
        node["props"] = props
    return node


def render(state):
    """The UI tree for one read. Missing fields are skipped, never an error."""
    thread = state.get("thread") or {}
    usage = thread.get("usage") or {}
    cwd = (thread.get("workspace") or {}).get("cwd") or os.getcwd()
    nova = nova_facts(cwd)
    kids = []

    kids.append(text(f"nova · {nova['level']}", "magenta", "bold"))
    if nova["tests"]:
        passed, failed = nova["tests"]
        kids.append(text(f"tests {passed}✓" + (f" {failed}✗" if failed else ""), "red" if failed else "green"))
    model = (thread.get("model") or {}).get("display_name")
    if model:
        kids.append(text(model, "cyan"))

    ctx = usage.get("context") or {}
    if ctx.get("used_percentage") is not None:
        pct = float(ctx["used_percentage"])
        size = ctx.get("context_window_size")
        tail = f" ({fmt(ctx.get('used_tokens'))}/{fmt(size)})" if ctx.get("used_tokens") is not None and size else ""
        kids.append(text(f"ctx {pct:.0f}%{tail}", pct_color(pct)))

    account = state.get("account") or {}
    for limit in account.get("rate_limits") or []:
        window = limit.get("primary_limit") or limit.get("secondary_limit")
        if window and window.get("used_percent") is not None:
            label = "5h" if (window.get("window_minutes") or 0) <= 300 else "wk"
            kids.append(text(f"{label} {float(window['used_percent']):.0f}%", pct_color(float(window["used_percent"]))))
            break

    total = usage.get("total") or {}
    if total:
        kids.append(text(f"↑{fmt(total.get('total_input_tokens'))} ↓{fmt(total.get('output_tokens'))} tok"))
    cost = (usage.get("cost") or {}).get("total_cost_usd")
    if cost is not None:
        kids.append(text(f"${float(cost):.2f} thread"))

    saved = f"saved ~{fmt(nova['saved_tokens'])} tok"
    if nova["saved_cost"] is not None:
        saved += f" · ${nova['saved_cost']:.2f}"
    if nova["saved_reads"]:
        saved += f" · {nova['saved_reads']} repeats"
    kids.append(text(saved, "green"))

    state_name = thread.get("agent", {}).get("state") if isinstance(thread.get("agent"), dict) else None
    if state_name:
        kids.append({"type": "italic", "children": [state_name]})
    return {"type": "row", "props": {"gap": 2, "wrap": "wrap"}, "children": kids}


def respond(method, params):
    if method == "initialize":
        return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "nova-statusline", "version": "0.20.0"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [TOOL]}
    if method == "tools/call":
        if (params or {}).get("name") != TOOL["name"]:
            raise ValueError("Unknown tool name")
        return {"content": [{"type": "text", "text": f"The statusline resource is {URI}."}]}
    if method == "resources/list":
        return {"resources": [{"name": "footer", "uri": URI, "mimeType": "application/json"}]}
    if method == "resources/templates/list":
        return {"resourceTemplates": []}
    if method == "resources/read":
        if (params or {}).get("uri") != URI:
            raise ValueError("Unknown resource URI")
        state = (params.get("_meta") or {}).get(STATE_FIELD) or {}
        return {"contents": [{"uri": URI, "mimeType": "application/json",
                              "text": json.dumps(render(state), ensure_ascii=False)}]}
    raise KeyError(method)


def main():
    for line in sys.stdin.buffer:
        reply = {"jsonrpc": "2.0", "id": None}
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(request.get("method"), str):
                reply["error"] = {"code": -32600, "message": "Invalid request"}
            elif "id" not in request:
                continue
            else:
                reply["id"] = request["id"]
                reply["result"] = respond(request["method"], request.get("params") or {})
        except json.JSONDecodeError:
            reply["error"] = {"code": -32700, "message": "Parse error"}
        except KeyError:
            reply["error"] = {"code": -32601, "message": "Method not found"}
        except (TypeError, ValueError, AttributeError):
            reply["error"] = {"code": -32602, "message": "Invalid parameters"}
        print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
