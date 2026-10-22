#!/usr/bin/env python3
"""Install or upgrade Plumbline in the git repository you are standing in — macOS, Linux and Windows.

    git clone https://github.com/umeshkumarkv/plumbline ~/plumbline
    cd <your-project>
    python3 ~/plumbline/install.py --jira <KEY>        # Windows: py %USERPROFILE%\\plumbline\\install.py --jira <KEY>

Fresh repository → copies .plumbline/ and runs init.py. Existing install (.plumbline/ or the older .agentic-sdlc/) →
upgrade, keeping project.yaml and the gate baseline. Every other argument is passed to init.py (--jira, --ci, ...).
"""
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit(f"Plumbline needs Python 3.10 or newer (this is {sys.version.split()[0]}).")
if sys.platform == "win32" and not sys.flags.utf8_mode:      # Windows: read and write UTF-8 like macOS/Linux
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))

SRC = Path(__file__).resolve().parent


def main():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Run this from inside your project's git repository.")
    target = Path(r.stdout.strip()).resolve()
    if target == SRC:
        sys.exit("Run this from your project, not from the plumbline checkout.")
    version = (SRC / "VERSION").read_text().strip()
    with tempfile.TemporaryDirectory() as tmp:
        kit = Path(tmp) / "kit"
        subprocess.run([sys.executable, str(SRC / "tools" / "make_kit.py"), "--out", str(kit)], check=True,
                       stdout=subprocess.DEVNULL)
        g = target / ".plumbline"
        if (g / "loops").is_dir() or (target / ".agentic-sdlc").is_dir():
            print(f"Upgrading Plumbline in {target} to {version}")
            tarball = Path(tmp) / "plumbline.tar.gz"
            with tarfile.open(tarball, "w:gz") as t:
                t.add(kit / ".plumbline", arcname=".plumbline")
            g.mkdir(exist_ok=True)
            shutil.copyfile(kit / ".plumbline" / "init.py", g / "init.py")
            cmd = [sys.executable, str(g / "init.py"), "--upgrade", str(tarball), *sys.argv[1:]]
        else:
            print(f"Installing Plumbline {version} in {target}")
            shutil.copytree(kit / ".plumbline", g)
            cmd = [sys.executable, str(g / "init.py"), *sys.argv[1:]]
        return subprocess.call(cmd, cwd=target)


if __name__ == "__main__":
    sys.exit(main())
