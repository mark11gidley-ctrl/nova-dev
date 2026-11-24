"""Engine-aware game checks. Used through: nd.py game <name> [root]

  engine-detect [root]     which engine the folder is (Godot, Unity, Web, Pygame) and why
  godot-scenes [root]      .tscn/.tres files that reference resources which do not exist
  unity-meta [root]        scripts and assets with no .meta file, and .meta files with no asset
  web-assets [root]        files that HTML or JS reference but that are not on disk
  web-bundle-size [root]   total size of JavaScript, CSS and media in the folder

Read-only.
"""
import json
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "Library", "Temp", "obj"}


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield os.path.join(dirpath, f)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def engine_detect(root):
    found = []
    if os.path.isfile(os.path.join(root, "project.godot")):
        found.append(("Godot", "project.godot"))
    if os.path.isfile(os.path.join(root, "ProjectSettings", "ProjectVersion.txt")):
        found.append(("Unity", "ProjectSettings/ProjectVersion.txt"))
    pkg = os.path.join(root, "package.json")
    if os.path.isfile(pkg):
        deps = json.loads(read(pkg) or "{}")
        blob = json.dumps(deps)
        if "phaser" in blob or "pixi" in blob or "three" in blob:
            found.append(("Web (JS/TS game library)", "package.json depends on a game library"))
        else:
            found.append(("Web", "package.json"))
    if any(f.endswith(".py") and "import pygame" in read(os.path.join(root, f)) for f in os.listdir(root)
           if os.path.isfile(os.path.join(root, f))):
        found.append(("Pygame", "a .py file imports pygame"))
    if not found and os.path.isfile(os.path.join(root, "index.html")):
        found.append(("Web", "index.html"))
    if not found:
        return ["no game engine detected; the engine-agnostic tools still work"]
    return [f"{name}: {why}" for name, why in found]


def godot_scenes(root):
    rows = []
    for path in walk(root):
        if not path.endswith((".tscn", ".tres")):
            continue
        for ref in re.findall(r'path="res://([^"]+)"', read(path)):
            if not os.path.exists(os.path.join(root, ref)):
                rows.append(f"{os.path.relpath(path, root)}: missing resource res://{ref}")
    return rows or ["every referenced resource exists"]


def unity_meta(root):
    rows = []
    assets = os.path.join(root, "Assets")
    if not os.path.isdir(assets):
        return ["no Assets folder: not a Unity project"]
    for path in walk(assets):
        if path.endswith(".meta"):
            if not os.path.exists(path[:-5]):
                rows.append(f"orphan meta (asset missing): {os.path.relpath(path, root)}")
        elif not path.endswith(".meta") and not os.path.exists(path + ".meta"):
            rows.append(f"no .meta: {os.path.relpath(path, root)}")
    return rows or ["every asset has a .meta file"]


def web_assets(root):
    rows = []
    ref = re.compile(r"""(?:src|href)=["']([^"'#?]+)["']|["']([^"'\s]+\.(?:png|jpe?g|gif|webp|svg|mp3|ogg|wav|json|css|js))["']""", re.I)
    for path in walk(root):
        if not path.endswith((".html", ".js", ".ts")):
            continue
        for m in ref.finditer(read(path)):
            target = (m.group(1) or m.group(2) or "").strip()
            if not target or target.startswith(("http:", "https:", "//", "data:", "#")):
                continue
            base = os.path.dirname(path) if path.endswith(".html") else root
            if not os.path.exists(os.path.join(base, target.lstrip("/"))) and not os.path.exists(os.path.join(root, target.lstrip("/"))):
                rows.append(f"{os.path.relpath(path, root)}: missing {target}")
    return rows or ["every referenced local file exists"]


def web_bundle_size(root, top=5):
    sizes = []
    for path in walk(root):
        if path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".ogg", ".wav", ".svg")):
            sizes.append((os.path.getsize(path), os.path.relpath(path, root)))
    sizes.sort(reverse=True)
    total = sum(s for s, _ in sizes)
    return [f"{s / 1048576:8.2f} MB  {p}" for s, p in sizes[:top]] + [f"total {total / 1048576:.2f} MB"]


COMMANDS = {"engine-detect": engine_detect, "godot-scenes": godot_scenes, "unity-meta": unity_meta,
            "web-assets": web_assets, "web-bundle-size": web_bundle_size}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    root = argv[1] if len(argv) > 1 else os.getcwd()
    for r in COMMANDS[argv[0]](root):
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
