"""Settings: one place for every knob. Precedence: environment variable, then config.json in the
state folder, then the built-in default. Secrets are never printed by summary()."""
import json
import os

from state import state_dir

DEFAULTS = {
    "level": "unset",  # the user chooses: off, lite, full or ultra
    "context_warn": 150_000,
    "window": 200_000,
    "autocompact": False,
    "ledger": True,
    "webhook_url": "",
    "webhook_token": "",
    "send_names": False,  # privacy: task names (prompt text) leave the machine only when you opt in
    "big_read": 0,
    # prices in dollars per million tokens; 0 means not set, so the report shows no money figure
    "price_input": 0.0,
    "price_output": 0.0,
    "price_cache_read": 0.0,
    "price_cache_write": 0.0,
    # your plan limit in tokens over the last 7 days; 0 means not set
    "plan_limit_tokens": 0,
    # "full" loads the complete rules each session; "short" loads one line (fewer tokens every session)
    "rules_style": "full",
}
ENV = {
    "level": "NOVA_DEV_DEFAULT",
    "context_warn": "NOVA_DEV_CONTEXT_WARN",
    "window": "NOVA_DEV_WINDOW",
    "autocompact": "NOVA_DEV_AUTOCOMPACT",
    "ledger": "NOVA_DEV_LEDGER",
    "webhook_url": "NOVA_DEV_WEBHOOK_URL",
    "webhook_token": "NOVA_DEV_WEBHOOK_TOKEN",
    "send_names": "NOVA_DEV_SEND_NAMES",
    "big_read": "NOVA_DEV_BIG_READ",
    "price_input": "NOVA_DEV_PRICE_INPUT",
    "price_output": "NOVA_DEV_PRICE_OUTPUT",
    "price_cache_read": "NOVA_DEV_PRICE_CACHE_READ",
    "price_cache_write": "NOVA_DEV_PRICE_CACHE_WRITE",
    "plan_limit_tokens": "NOVA_DEV_PLAN_LIMIT_TOKENS",
    "rules_style": "NOVA_DEV_RULES_STYLE",
}
SECRET = {"webhook_token"}


def config_path():
    return os.path.join(state_dir(), "config.json")


def _coerce(key, raw):
    default = DEFAULTS[key]
    if isinstance(default, bool):
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    return str(raw)


def _file_config():
    try:
        with open(config_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


ENV_ONLY = {"webhook_token"}  # secrets are read from the environment only, never from a file


def get(key):
    env = os.environ.get(ENV[key], "")
    if env != "":
        try:
            return _coerce(key, env)
        except ValueError:
            pass
    if key in ENV_ONLY:
        return DEFAULTS[key]
    cfg = _file_config()
    if key in cfg:
        try:
            return _coerce(key, cfg[key])
        except (ValueError, TypeError):
            pass
    return DEFAULTS[key]


def summary():
    """Settings as text for humans. Secrets are reported as set or not set, never shown."""
    lines = []
    for key in DEFAULTS:
        value = get(key)
        if key in SECRET:
            value = "set" if value else "not set"
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
