"""Set up what nova-dev needs. Usage: python -I scripts/setup.py [--yes]

Checks for Python 3, Git, Node.js, ffmpeg and the Codex CLI. Prints what is missing and the exact
command that would install each item. Installs nothing unless you pass --yes or answer y at the
prompt. Installs use the system package manager: winget (Windows), brew (macOS), apt (Linux).

Each command runs without a shell, so nothing here is interpreted by one.
"""
import os
import platform
import shutil
import subprocess
import sys

# name, how to detect it, Windows install, macOS install, Linux install, required?
# Where the Windows installers put programs, so a program is found even when PATH in this shell is stale.
KNOWN_WIN = {
    "node": r"C:\Program Files\nodejs\node.exe",
    "ffmpeg": r"C:\Users\{user}\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
    "codex": r"C:\Users\{user}\AppData\Roaming\npm\codex.cmd",
}


def _known(name):
    if os.name != "nt" or name not in KNOWN_WIN:
        return False
    path = KNOWN_WIN[name].format(user=os.environ.get("USERNAME", ""))
    return os.path.isfile(path)


ITEMS = [
    ("Python 3.9+", ["python3", "python", "py"], ["winget", "install", "-e", "--id", "Python.Python.3.13", "--silent",
                                               "--accept-package-agreements", "--accept-source-agreements"],
     ["brew", "install", "python"], ["sudo", "apt-get", "install", "-y", "python3"], True),
    ("Git", ["git"], ["winget", "install", "-e", "--id", "Git.Git", "--silent", "--accept-package-agreements",
                     "--accept-source-agreements"],
     ["brew", "install", "git"], ["sudo", "apt-get", "install", "-y", "git"], True),
    ("Node.js (LTS)", ["node"], ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS", "--silent",
                                 "--accept-package-agreements", "--accept-source-agreements"],
     ["brew", "install", "node"], ["sudo", "apt-get", "install", "-y", "nodejs", "npm"], True),
    ("ffmpeg (video tools)", ["ffmpeg"], ["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--silent",
                                          "--accept-package-agreements", "--accept-source-agreements"],
     ["brew", "install", "ffmpeg"], ["sudo", "apt-get", "install", "-y", "ffmpeg"], False),
    ("Codex CLI (ChatGPT/Codex)", ["codex"], ["npm", "install", "-g", "@openai/codex"],
     ["npm", "install", "-g", "@openai/codex"], ["npm", "install", "-g", "@openai/codex"], False),
]


def os_kind():
    system = platform.system()
    return {"Windows": "win", "Darwin": "mac"}.get(system, "linux")


def missing(which=shutil.which):
    """Items whose detection command is not on PATH. Returns (name, install_argv, required) tuples."""
    kind = os_kind()
    index = {"win": 2, "mac": 3, "linux": 4}[kind]
    out = []
    for name, detect, *installs, required in ITEMS:
        if not any(which(d) or _known(d) for d in detect):
            out.append((name, installs[index - 2], required))
    return out


def install(argv, runner=subprocess.run, which=shutil.which):
    # resolve the program first: on Windows, npm is npm.cmd, which subprocess cannot find by bare name
    exe = which(argv[0]) or argv[0]
    return runner([exe] + argv[1:], check=False).returncode == 0


def main(argv):
    auto_yes = "--yes" in argv
    items = missing()
    if not items:
        print("Everything nova-dev needs is installed.")
        return 0
    print("Missing:")
    for name, cmd, required in items:
        tag = "required" if required else "optional"
        print(f"  - {name} ({tag}): {' '.join(cmd)}")
    if not auto_yes and not sys.stdin.isatty():
        print("\nNothing installed. Run again with --yes to install, or run it in a terminal to choose each item.")
        return 0
    failures = 0
    for name, cmd, required in items:
        if not auto_yes:
            answer = input(f"Install {name}? [y/N] ").strip().lower()
            if answer != "y":
                print(f"  skipped {name}")
                continue
        if shutil.which(cmd[0]) is None:
            print(f"  cannot install {name}: {cmd[0]} is not available. Install it first.")
            failures += 1
            continue
        print(f"  installing {name} ...")
        ok = install(cmd)
        print(f"  {'done' if ok else 'FAILED'}: {name}")
        failures += 0 if ok else 1
    print("\nOpen a new terminal so the new programs are on PATH, then run: python -I scripts/doctor.py")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
