#!/usr/bin/env python3
"""Plumbline Guardrails gate runner.

Runs Semgrep rules + structural checks against a repo and applies a ratchet baseline:
existing violations (recorded in the baseline) are reported as debt; any NEW violation fails.

  run_gates.py <repo> --baseline gates/baseline.json            # check (exit 1 on new findings)
  run_gates.py <repo> --write-baseline gates/baseline.json      # record current debt
  run_gates.py <repo> --json                                     # machine-readable findings
  run_gates.py <repo> --all-packs                                # every pack/check (self-tests, eval harness)

Fingerprint = rule + path + whitespace-normalised source line, so findings survive
line-number shifts but a changed offending line counts as new.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "impact"))
import layout  # noqa: E402
RULES = HERE / "semgrep"          # rule packs (*.yml)
ALL_PACKS = False
GENERIC_PACKS, GENERIC_CHECKS = ["java-generic.yml"], ["structure_check"]   # any Spring/Java repository
ALL_CHECKS = {"structure_check": HERE / "checks" / "structure_check.py", "domain_check": HERE / "checks" / "domain_check.py"}
# The configuration that judges a repository is the one next to THIS script (in CI: the base branch's copy), never the
# pull request's: a PR cannot switch gates off or redeclare units.
CONFIG = HERE.parent / "project.yaml"
layout.TRUSTED_CONFIG = str(CONFIG)   # missing file = auto-detect; never fall back to the scanned repo's own file


def gate_config():
    """`gates:` in project.yaml — {semgrep: [packs], checks: [names]}. Without it: the generic set only."""
    if ALL_PACKS:                    # self-tests and the eval harness: every pack and check in this folder
        return sorted(RULES.glob("*.yml")), list(ALL_CHECKS.values())
    g = (layout.project(config=CONFIG) or {}).get("gates") or {}
    packs = g.get("semgrep", GENERIC_PACKS)
    files = [RULES / x for x in packs]
    missing = [str(f) for f in files if not f.is_file()]
    if missing:
        raise SystemExit(f"gates: rule pack(s) not found: {missing}")
    names = g.get("checks", GENERIC_CHECKS)
    unknown = [n for n in names if n not in ALL_CHECKS]
    if unknown:
        raise SystemExit(f"gates: unknown check(s) {unknown}; known: {list(ALL_CHECKS)}")
    return files, [ALL_CHECKS[n] for n in names]


def source_line(repo: Path, path: str, line: int) -> str:
    try:
        return (repo / path).read_text(errors="ignore").splitlines()[line - 1]
    except Exception:
        return ""


def fingerprint(f, repo):
    norm = " ".join(source_line(repo, f["path"], f["line"]).split())
    return hashlib.sha256(f"{f['rule']}|{f['path']}|{norm}".encode()).hexdigest()[:16]


SCAN_EXT = {".java", ".yml", ".yaml", ".properties", ".xml", ".sql", ".kt"}


# Directory names Semgrep skips by default (its built-in ignore list) — renamed in the scan copy
SEMGREP_SKIPPED_DIRS = {"test", "tests", "vendor", "build", "dist", "node_modules", "target", "env", "venv",
                        "bower_components", "jspm_packages", "__pycache__"}


def neutral_path(rel: Path) -> str:
    """Map a file to a path Semgrep cannot skip. Directory names that Semgrep ignores by default (e.g. a Java
    package named `vendor` or `test` under src/main/java) or that start with '.' get a `_` prefix. The standard
    `src/test/` folder keeps its name so the rules' `exclude: **/src/test/**` still applies."""
    parts = list(rel.parts)
    for i, d in enumerate(parts[:-1]):
        standard_test = d == "test" and i > 0 and parts[i - 1] == "src"
        if (d.lower() in SEMGREP_SKIPPED_DIRS or d.startswith(".")) and not standard_test:
            parts[i] = "z_" + d.lstrip(".")
    return "/".join(parts)


def run_semgrep(repo: Path, units=None):
    # Scan a sanitised copy so nothing in the repo can hide code from the gate: repo ignore files (.semgrepignore,
    # .gitignore), inline nosemgrep (--disable-nosem), Semgrep's built-in path ignores (neutral paths) and its
    # 1 MB size limit (--max-target-bytes 0). Fails closed if Semgrep does not complete.
    import os
    import tempfile
    links = sorted(str(f.relative_to(repo)) for f in (repo / "services").rglob("*") if f.is_symlink())
    if links:   # a symlink could point source code at an unscanned file; no legitimate need for one under services/
        raise SystemExit(f"symlinks under services/ are not allowed (gate cannot vouch for their target): {links[:3]}")
    roots = [repo / "services" / u for u in units] if units else [repo / "services"]
    files = sorted(f for r in roots if r.is_dir() for f in r.rglob("*")
                   if f.is_file() and f.suffix in SCAN_EXT and not f.is_symlink()
                   and not (len(f.relative_to(repo).parts) > 2 and f.relative_to(repo).parts[2] == "target"))
    bad = []
    for f in files:   # a re-encoded file (e.g. via .gitattributes working-tree-encoding) would parse as nothing
        if f.suffix in (".java", ".yml", ".yaml", ".properties"):
            raw = f.read_bytes()
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                bad.append(str(f.relative_to(repo)))
                continue
            if b"\0" in raw:
                bad.append(str(f.relative_to(repo)))
    if bad:
        raise SystemExit(f"source files that are not plain UTF-8 text cannot be gated: {bad[:3]} — failing closed")
    back = {}
    with tempfile.TemporaryDirectory() as td:
        for f in files:
            rel = f.relative_to(repo)
            dst = neutral_path(rel)
            back[dst] = str(rel)
            (Path(td) / dst).parent.mkdir(parents=True, exist_ok=True)
            (Path(td) / dst).write_bytes(f.read_bytes())
        out = subprocess.run(
            ["semgrep", "scan", *[a for f in gate_config()[0] for a in ("--config", str(f))], "--metrics=off", "--disable-version-check",
             "--disable-nosem", "--no-git-ignore", "--max-target-bytes", "0", "--json", "-q", "services"],
            cwd=td, capture_output=True, text=True,
            env={**os.environ, "SEMGREP_ENABLE_VERSION_CHECK": "0", "SEMGREP_SEND_METRICS": "off"})
    if out.returncode not in (0, 1):
        raise SystemExit(f"semgrep failed (exit {out.returncode}): {out.stderr[-500:]}")
    try:
        data = json.loads(out.stdout)
        results = data["results"]
    except (ValueError, KeyError):
        raise SystemExit("semgrep produced no parseable results — failing closed")
    if data.get("errors"):
        raise SystemExit(f"semgrep errors: {data['errors'][:2]}")
    # Every production Java file and every main resources YAML file must have been scanned.
    must = {d for d in back if ("/src/main/java/" in d and d.endswith(".java"))
            or ("/src/main/resources/" in d and d.endswith((".yml", ".yaml")))}
    scanned = set(data.get("paths", {}).get("scanned", []))
    if must - scanned:
        skipped = sorted(back[p] for p in must - scanned)
        raise SystemExit(f"semgrep skipped {len(skipped)} file(s), e.g. {skipped[:3]} — failing closed")
    res, seen = [], set()
    for r in results:
        key = (r["check_id"], r["path"], r["start"]["line"])
        if key in seen:      # one finding per rule per line
            continue
        seen.add(key)
        res.append({"rule": r["check_id"].split(".")[-1], "path": back.get(r["path"], r["path"]),
                    "line": r["start"]["line"], "message": r["extra"]["message"],
                    "severity": r["extra"]["severity"], "engine": "semgrep"})
    return res


def run_struct(repo: Path):
    res = []
    for check in gate_config()[1]:
        out = subprocess.run([sys.executable, str(check), str(repo)], capture_output=True, text=True, check=True)  # check=True: fail closed
        for line in out.stdout.splitlines():
            f = json.loads(line)
            f.update(severity="ERROR", engine=check.stem)
            res.append(f)
    return res


def gate_view(repo: Path):
    """The checks expect backends under services/<name>/. For any other layout (a root app, top-level modules,
    .plumbline/project.yaml) build a copy where each backend unit sits at services/<name>/ and everything else
    keeps its path. Returns (view_dir, to_repo_path) — or (repo, identity) when the layout is already standard."""
    units = [u for u in layout.units(repo, config=CONFIG) if u["kind"] == "service"]
    if all(u["path"] == f"services/{u['name']}" for u in units):
        return repo, None
    import shutil
    import tempfile
    view = Path(tempfile.mkdtemp(prefix="gates-view-"))
    every = layout.units(repo, config=CONFIG)
    prefix = {}
    for f in repo.rglob("*"):
        rel = f.relative_to(repo).as_posix()
        top = rel.split("/")[0]
        if top in (".git", ".plumbline", ".agentic-sdlc", ".guardrails") or "/node_modules/" in "/" + rel \
                or "/target/" in "/" + rel:
            continue
        u = layout.unit_of(rel, every)
        if f.is_symlink() and u and u["kind"] == "service":   # same rule as services/: fail closed
            raise SystemExit(f"symlinks in a backend unit are not allowed (gate cannot vouch for their target): {rel}")
        if not f.is_file() or f.is_symlink():
            continue
        if u and u["kind"] == "service" and u["path"] != f"services/{u['name']}":
            inner = rel if u["path"] == "." else rel[len(u["path"]) + 1:]
            dst = f"services/{u['name']}/{inner}"
            prefix[f"services/{u['name']}/"] = "" if u["path"] == "." else u["path"] + "/"
        else:
            dst = rel
        target = (view / dst).resolve()
        if not str(target).startswith(str(view.resolve()) + "/"):
            raise SystemExit(f"gate view: {rel} maps outside the scan copy ({dst}) — failing closed")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, target)
    def back(path):
        for v, r in prefix.items():
            if path.startswith(v):
                return r + path[len(v):]
        return path
    return view, back


def changed_units(repo: Path, base: str):
    """Backend units a PR touches (git diff against the merge base), by unit name."""
    mb = subprocess.run(["git", "-C", str(repo), "merge-base", base, "HEAD"], capture_output=True, text=True,
                        check=True).stdout.strip()
    out = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", mb, "HEAD"], capture_output=True, text=True,
                         check=True).stdout.splitlines()
    every = layout.units(repo, config=CONFIG)
    return sorted({u["name"] for p in out for u in [layout.unit_of(p, every)] if u and u["kind"] == "service"})


def collect(repo: Path, units=None):
    """All findings; with `units`, Semgrep scans only those services and findings are limited to them
    (the Python checks still read the whole repo, since some rules compare services). Paths are reported as they
    are in the repository, whatever its layout."""
    view, back = gate_view(repo)
    try:
        findings = run_semgrep(view, units) + run_struct(view)
        if units:
            keep = tuple(f"services/{u}/" for u in units)
            findings = [f for f in findings if f["path"].startswith(keep)]
    finally:
        if back:
            import shutil
            shutil.rmtree(view, ignore_errors=True)
    for f in findings:
        if back:
            f["path"] = back(f["path"])
            f["message"] = f["message"].replace("services/<svc>", "the unit")
        f["fingerprint"] = fingerprint(f, repo)
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--baseline")
    ap.add_argument("--write-baseline")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--changed-from", help="only gate services changed since this git ref (large monorepos)")
    ap.add_argument("--all-packs", action="store_true", help="every Semgrep pack and check, ignoring project.yaml")
    a = ap.parse_args()
    global ALL_PACKS
    ALL_PACKS = a.all_packs
    if a.baseline and not Path(a.baseline).is_file():
        print(f"gates: baseline {a.baseline} not found — create it: python3 .plumbline/init.py --rebaseline, then commit")
        return 2
    repo = Path(a.repo).resolve()
    units = changed_units(repo, a.changed_from) if a.changed_from else None
    if units is not None and not units:
        print("gates: no service changed")
        return 0
    findings = collect(repo, units)

    if a.write_baseline:
        counts = Counter(f["fingerprint"] for f in findings)
        Path(a.write_baseline).write_text(json.dumps(
            {"fingerprints": dict(sorted(counts.items())),
             "findings": [{k: f[k] for k in ("rule", "path", "line")} for f in findings]}, indent=1))
        print(f"baseline written: {len(findings)} findings")
        return 0

    known = Counter()
    if a.baseline:
        fp = json.loads(Path(a.baseline).read_text())["fingerprints"]
        known = Counter(fp) if isinstance(fp, dict) else Counter({k: 1 for k in fp})
    # A fingerprint is debt only up to the number of times it was recorded; extra copies are NEW.
    seen, new = Counter(), []
    for f in findings:
        seen[f["fingerprint"]] += 1
        if seen[f["fingerprint"]] > known[f["fingerprint"]]:
            new.append(f)
    if a.json:
        print(json.dumps({"total": len(findings), "new": new}, indent=1))
    else:
        print(f"gates: {len(findings)} findings, {len(findings) - len(new)} baseline debt, {len(new)} NEW")
        for f in new:
            print(f"  NEW {f['rule']:32} {f['path']}:{f['line']}  {f['message'][:110]}")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
