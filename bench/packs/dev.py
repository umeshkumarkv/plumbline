"""Dev benchmark — the code change (dev-eval-loop Step B/C). Also used by code-review on the pinned PR worktree.
Runs the deterministic gates, the cross-service impact check and reads test + coverage evidence.
Judge keeps: logic and domain correctness, design adherence, test quality, the categories gates cannot see."""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from common import ROOT, UsageError, git_ok_ref

sys.path.insert(0, str(ROOT / "impact"))
import layout  # noqa: E402

UNITS = {}   # changed backend unit name -> its directory relative to the repo ("" for a root app, else "path/")


def changed_services(repo: Path, base: str):
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=repo, capture_output=True, text=True)
    out2 = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=repo, capture_output=True, text=True)   # uncommitted
    out3 = subprocess.run(["git", "ls-files", "-o", "--exclude-standard"], cwd=repo, capture_output=True, text=True)  # new files
    files = set(out.stdout.split()) | set(out2.stdout.split()) | {f for f in out3.stdout.split() if not f.startswith(".plumbline/")}
    units = layout.units(repo)
    UNITS.clear()
    for f in files:
        u = layout.unit_of(f, units)
        if u and u["kind"] == "service":
            UNITS[u["name"]] = "" if u["path"] == "." else u["path"] + "/"
    return sorted(UNITS), sorted(files)


def run(r, ctx):
    repo = ctx.repo.path
    if not repo:
        raise UsageError("pass --repo (the working tree with the change)")
    ctx.base = ctx.base or "develop"
    if not git_ok_ref(repo, ctx.base):
        raise UsageError(f"--base {ctx.base} is not a commit in {repo}")
    svcs, files = changed_services(repo, ctx.base)
    r.add("DEV-0", "Change touches a backend unit", bool(svcs), f"changed services: {svcs or 'none'}; {len(files)} files", warn=not svcs)

    # 1. deterministic gates (Semgrep + structure + domain), baseline ratchet, nosemgrep ignored
    cmd = [sys.executable, str(ROOT / "gates/run_gates.py"), str(repo), "--json",
           "--baseline", str(ROOT / "gates/baseline.json"), "--changed-from", ctx.base]
    g = subprocess.run(cmd, capture_output=True, text=True)
    try:
        new = json.loads(g.stdout)["new"]
        r.add("DEV-1", "Gates: 0 NEW violations", not new, f"{len(new)} new",
              [f"{f['rule']} {f['path']}:{f['line']}" for f in new])
    except (ValueError, KeyError):
        r.add("DEV-1", "Gates ran", False, f"gate runner failed (exit {g.returncode}): {(g.stderr or g.stdout)[-300:]}")

    # 2. cross-service impact: nothing left pointing at something removed/moved
    imp = ctx.workdir / "impact.json"
    i = subprocess.run([sys.executable, str(ROOT / "impact/impact.py"), "--repo", str(repo), "--base", ctx.base,
                        "--json", str(imp), "--bundle", str(ctx.workdir / "impact.md")]
                       + (["--cache", ctx.cache] if ctx.cache else []), capture_output=True, text=True)
    try:
        res = json.loads(imp.read_text())
        r.add("DEV-2", "Impact: no BREAKING contract change", not res["breaking"], f"{len(res['breaking'])} breaking",
              res["breaking"])
        aff = sorted(res["affected"])
        r.add("DEV-3", "Impact: affected services listed for the judge", not aff,
              f"affected: {aff} — the judge must check impact.md counterparts" if aff else "no other service affected", warn=True)
    except (OSError, ValueError, KeyError):
        r.add("DEV-2", "Impact check ran", False, f"impact.py failed (exit {i.returncode}): {(i.stderr or i.stdout)[-300:]}")

    # 3. tests: surefire reports must exist for every changed backend service and show 0 failures/errors
    if ctx.test_cmd:
        t = subprocess.run(ctx.test_cmd, shell=True, cwd=repo, capture_output=True, text=True)
        r.add("DEV-4a", f"Test command passed: {ctx.test_cmd}", t.returncode == 0, f"exit {t.returncode}", t.stdout.splitlines()[-15:])
    totals, missing = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}, []
    failing, stale = [], []
    newest_src = {s: max([(repo / f).stat().st_mtime for f in files if f.startswith(f"{UNITS[s]}src/") and (repo / f).exists()] or [0])
                  for s in svcs}
    for s in svcs:
        reps = list((repo / UNITS[s] / "target/surefire-reports").glob("TEST-*.xml"))
        if not reps and (repo / UNITS[s] / "pom.xml").exists():
            missing.append(s)
        if reps and max(p.stat().st_mtime for p in reps) < newest_src[s]:
            stale.append(s)
        for rep in reps:
            try:
                root = ET.parse(rep).getroot()
            except ET.ParseError:
                continue
            for k in totals:
                totals[k] += int(root.get(k, 0) or 0)
            for tc in root.iter("testcase"):
                if tc.find("failure") is not None or tc.find("error") is not None:
                    failing.append(f"{s}: {tc.get('classname')}.{tc.get('name')}")
    if stale:
        r.add("DEV-4", "Test reports are newer than the changed code", False,
              f"surefire reports older than the latest source change in {stale} — re-run the tests")
    elif missing:
        r.add("DEV-4", "Test reports present for every changed service", False,
              f"no surefire reports for {missing} — run `mvn test` (Step C) before the benchmark")
    else:
        r.add("DEV-4", "Unit tests: 0 failures, 0 errors", totals["tests"] > 0 and not failing,
              f"{totals['tests']} tests, {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped", failing)

    # 4. coverage: JaCoCo line coverage >= threshold per changed service
    low, seen = [], []
    for s in svcs:
        csv = repo / UNITS[s] / "target/site/jacoco/jacoco.csv"
        if not csv.exists():
            continue
        miss = cov = 0
        for line in csv.read_text().splitlines()[1:]:
            c = line.split(",")
            if len(c) > 8:
                miss, cov = miss + int(c[7]), cov + int(c[8])
        pct = 100 * cov / (miss + cov) if miss + cov else 0
        seen.append(f"{s} {pct:.1f}%")
        if pct < ctx.min_coverage:
            low.append(f"{s} {pct:.1f}%")
    if seen:
        r.add("DEV-5", f"Line coverage >= {ctx.min_coverage}% (JaCoCo)", not low, ", ".join(seen), low)
    else:
        r.add("DEV-5", f"Line coverage >= {ctx.min_coverage}%", False, "no jacoco.csv found — run `mvn verify` with JaCoCo", warn=True)

    # 5. each changed main class has a test that names it (cheap traceability; the judge rates test quality)
    untested = []
    for f in files:
        m = re.match(r"(.*?)src/main/java/(.+)/(\w+(?:Service|Controller|Consumer|Producer|Rule))\.java$", f)
        if m and (repo / f).exists() and m.group(1) in UNITS.values():
            name = m.group(3)
            if not list((repo / m.group(1) / "src/test").rglob(f"{name}*Test.java")):
                untested.append(f)
    r.add("DEV-6", "Every changed Service/Controller/Consumer/Producer/Rule has a *Test", not untested,
          f"{len(untested)} without a test class", untested)
