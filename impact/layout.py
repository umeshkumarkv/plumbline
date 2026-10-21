#!/usr/bin/env python3
"""Where the deployable units of a repository live — the one place every check asks.

  python3 impact/layout.py [REPO] [--ref REF]       prints the units as JSON: [{"name", "path", "kind", "build"}]

Supported layouts (detected in this order; a unit is listed once):
  1. `.plumbline/project.yaml` with `units: [{name, path, kind: service|frontend}]` — explicit, always wins
  2. `services/<name>/`                            a backend service per folder (the broker-dealer layout)
  3. `<dir>/` with pom.xml / build.gradle(.kts) and src/main/  a backend module at the top level
  4. the repository root, with pom.xml / build.gradle(.kts) and src/main/  a single app at the root (path ".")
  5. `<dir>/` with package.json                    a frontend
A unit at "." owns `src/` and the build files; its CLAUDE.md is `src/CLAUDE.md`. The root CLAUDE.md is the master file
(solution and architecture) and belongs to no unit. Other units' folders are not part of the root unit.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

BUILD_FILES = ("pom.xml", "build.gradle", "build.gradle.kts")
NAME = re.compile(r"[A-Za-z0-9][\w.-]*")
SKIP_TOP = {"node_modules", "target", "build", "dist", "docs", "doc", "scripts"}
ROOT_OWNS = ["src", "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
             "gradle", ".mvn", "mvnw", "mvnw.cmd", "gradlew", "gradlew.bat"]


class Tree:
    """The working tree, or a git revision read without checking it out."""

    def __init__(self, repo: Path, ref=None):
        self.repo, self.ref = Path(repo).resolve(), ref
        self._paths = None
        if ref:
            out = subprocess.run(["git", "-C", str(self.repo), "ls-tree", "-r", "-t", "--name-only", ref],
                                 capture_output=True, text=True, check=True).stdout
            self._paths = set(out.splitlines())

    def exists(self, rel):
        return rel in self._paths if self._paths is not None else (self.repo / rel).exists()

    def is_dir(self, rel):
        if self._paths is not None:
            return any(p.startswith(rel.rstrip("/") + "/") for p in self._paths)
        return (self.repo / rel).is_dir()

    def dirs(self, rel=""):
        if self._paths is not None:
            pre = rel.rstrip("/") + "/" if rel else ""
            return sorted({p[len(pre):].split("/")[0] for p in self._paths
                           if p.startswith(pre) and "/" in p[len(pre):]})
        d = self.repo / rel
        return sorted(x.name for x in d.iterdir() if x.is_dir()) if d.is_dir() else []

    def read(self, rel):
        if self._paths is not None:
            return subprocess.run(["git", "-C", str(self.repo), "show", f"{self.ref}:{rel}"],
                                  capture_output=True, text=True).stdout
        p = self.repo / rel
        return p.read_text(errors="replace") if p.is_file() else ""


def _build(t, rel):
    pre = "" if rel == "." else rel + "/"
    for f in BUILD_FILES:
        if t.exists(pre + f):
            return "maven" if f == "pom.xml" else "gradle"
    return "npm" if t.exists(pre + "package.json") else None


def declared(t, config=None):
    """Units from project.yaml. `config` (a path) overrides the repository's own file — the gates pass the trusted
    copy (the base branch's), so a pull request cannot redeclare units to hide code."""
    text = Path(config).read_text() if config and Path(config).is_file() else ("" if config else t.read(".plumbline/project.yaml"))
    if not text.strip():
        return None
    import yaml
    cfg = yaml.safe_load(text) or {}
    units, names, paths = [], set(), set()
    for u in cfg.get("units") or []:
        path = str(u.get("path", "")).strip() or "."
        if path != "." and (path.startswith("/") or path.endswith("/") or not re.fullmatch(r"[\w.-]+(/[\w.-]+)*", path)
                            or any(x in (".", "..") for x in path.split("/"))):
            raise SystemExit(f"project.yaml: unit path {path!r} must be relative, without '..' (e.g. modules/billing)")
        kind = u.get("kind", "service")
        if kind not in ("service", "frontend"):
            raise SystemExit(f"project.yaml: unit {u}: kind must be service or frontend")
        name = str(u.get("name") or (Path(t.repo).name if path == "." else path.split("/")[-1]))
        if not NAME.fullmatch(name):
            raise SystemExit(f"project.yaml: unit name {name!r} must match {NAME.pattern}")
        if name in names or path in paths:
            raise SystemExit(f"project.yaml: duplicate unit name or path: {name} ({path})")
        if kind == "service" and path != f"services/{name}" and t.is_dir(f"services/{name}"):
            raise SystemExit(f"project.yaml: unit {name} at {path} collides with the folder services/{name}/")
        names.add(name); paths.add(path)
        units.append({"name": name, "path": path, "kind": kind, "build": u.get("build") or _build(t, path)})
    return units


TRUSTED_CONFIG = None   # set by the gates / impact CLIs (--config): the base branch's project.yaml, never the PR's


def units(repo, ref=None, config=None):
    t = Tree(repo, ref)
    d = declared(t, config or TRUSTED_CONFIG)
    if d is not None:
        return d
    out, seen = [], set()

    def add(name, path, kind):
        if not NAME.fullmatch(name):
            name = re.sub(r"[^\w.-]", "-", name).lstrip(".-") or "app"
        if path not in seen:
            seen.add(path)
            out.append({"name": name, "path": path, "kind": kind, "build": _build(t, path)})

    if t.is_dir("services"):
        for n in t.dirs("services"):
            add(n, f"services/{n}", "service")
    for n in t.dirs():
        if n.startswith(".") or n in SKIP_TOP or n == "services":
            continue
        if any(t.exists(f"{n}/{b}") for b in BUILD_FILES) and t.is_dir(f"{n}/src/main"):
            add(n, n, "service")
    if any(t.exists(b) for b in BUILD_FILES) and t.is_dir("src/main"):
        add(Path(t.repo).name, ".", "service")
    for n in t.dirs():
        if not n.startswith(".") and n not in SKIP_TOP and t.exists(f"{n}/package.json"):
            add(n, n, "frontend")
    return out


def owns(unit, rel, all_units):
    """Does `rel` (a repo-relative path) belong to `unit`? Nested units win over the root unit."""
    p = unit["path"]
    if p != ".":
        return rel == p or rel.startswith(p + "/")
    if any(u["path"] != "." and (rel == u["path"] or rel.startswith(u["path"] + "/")) for u in all_units):
        return False
    return rel.split("/")[0] in ROOT_OWNS or rel == "openapi.yaml"


def unit_of(rel, all_units):
    for u in sorted(all_units, key=lambda u: -len(u["path"])):
        if owns(u, rel, all_units):
            return u
    return None


def claude_md(unit):
    """Where a unit's own CLAUDE.md lives: <unit path>/CLAUDE.md, or src/CLAUDE.md for an app at the repository root
    (the root CLAUDE.md is the master file: solution and architecture)."""
    return "src/CLAUDE.md" if unit["path"] == "." else f"{unit['path']}/CLAUDE.md"


def code_globs(all_units):
    """Paths a code-writing role may change: every unit's own files. scope_check.py still denies Gradle build files
    and build wrappers (no guarded-parts check for them yet), and pom.xml keeps its guarded test/coverage parts."""
    g = []
    for u in all_units:
        g += ["src/*", "pom.xml"] if u["path"] == "." else [u["path"] + "/*"]
    return g


def project(repo=None, config=None):
    """The whole project.yaml (units, domain_pack, gates, base_branch, ...) or {}."""
    path = Path(config) if config else Path(repo or ".") / ".plumbline" / "project.yaml"
    if not path.is_file():
        return {}
    import yaml
    return yaml.safe_load(path.read_text()) or {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else None
    cfg = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else None
    args = [x for x in args if x not in (ref, cfg)]
    print(json.dumps(units(Path(args[0] if args else "."), ref, cfg), indent=1))


if __name__ == "__main__":
    main()
