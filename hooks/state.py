"""Shared level state. The level is one word in a file, so every hook reads the same value."""
import os

VALID = ("off", "lite", "full", "ultra")
UNSET = "unset"  # no level chosen yet: nova-dev stays inactive until the user picks one


def state_dir():
    return os.environ.get("NOVA_DEV_DIR") or os.path.join(os.path.expanduser("~"), ".config", "nova-dev")


def cache_dir():
    """Hook caches live in the private state folder, not the shared temp folder."""
    path = os.path.join(state_dir(), "cache")
    os.makedirs(path, exist_ok=True)
    return path


def write_private(path, text):
    """Write a file readable by the owner only where the OS supports it."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)


def project_config(cwd=None):
    """Per-project settings from .claude/nova-dev.json in the working folder. Empty dict when absent or invalid."""
    import json
    path = os.path.join(cwd or os.getcwd(), ".claude", "nova-dev.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get_level(cwd=None):
    """Level precedence: project file, then the typed level file, then the level setting.
    Returns UNSET when nothing is chosen, and every hook treats UNSET as inactive."""
    project = project_config(cwd).get("level")
    if project in VALID:
        return project
    try:
        with open(os.path.join(state_dir(), "level"), encoding="utf-8") as fh:
            value = fh.read().strip()
    except OSError:
        from settings import get as setting  # lazy: settings imports this module
        value = str(setting("level")).strip()
    return value if value in VALID else UNSET


def set_level(value):
    if value not in VALID:
        raise ValueError(f"level must be one of {VALID}")
    os.makedirs(state_dir(), exist_ok=True)
    with open(os.path.join(state_dir(), "level"), "w", encoding="utf-8") as fh:
        fh.write(value)
