#!/usr/bin/env python3
"""Build the copyable kit: build/kit/.plumbline/ — one folder with everything a repository needs.
  python3 tools/make_kit.py [--out build/kit]"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["loops", "dist", "bench", "gates", "impact", "packs", "selftest", "security", "CHANGELOG.md", "requirements.txt"]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "eval", "scale", "eval_impact.py", "tools")


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "build/kit"
    kit = out / ".plumbline"
    shutil.rmtree(kit, ignore_errors=True)
    kit.mkdir(parents=True)
    for name in INCLUDE:
        src = ROOT / name
        (shutil.copytree(src, kit / name, ignore=SKIP) if src.is_dir() else shutil.copy2(src, kit / name))
    shutil.copy2(ROOT / "tools/install.sh", kit / "install.sh")
    shutil.copy2(ROOT / "tools/init.py", kit / "init.py")
    shutil.copy2(ROOT / "tools/kit.gitignore", kit / ".gitignore")
    shutil.copy2(ROOT / "tools/KIT-README.md", kit / "README.md")
    shutil.copy2(ROOT / "tools/project.yaml.example", kit / "project.yaml.example")
    (kit / "VERSION").write_text((ROOT / "VERSION").read_text())
    print(f"kit: {kit}  ({sum(f.stat().st_size for f in kit.rglob('*') if f.is_file()) // 1024} KB)")


if __name__ == "__main__":
    main()
