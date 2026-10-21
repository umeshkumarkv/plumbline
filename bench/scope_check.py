#!/usr/bin/env python3
"""Scope check for Stage 1: an originator may change only what its role allows (deterministic, no LLM).

  scope_check.py snapshot --name N [--writable "GLOB ..."]
        Before calling the originator. Prints `SNAPSHOT <dir> <sha256>`: the snapshot and a private copy of this
        checker live OUTSIDE the repository (a fresh temp dir); the sha covers all three files. Then:
  test "$(cat <dir>/bench/scope_check.py <dir>/gates/checks/protected_paths.py <dir>/snapshot.json | sha256sum \
        | cut -d' ' -f1)" = <sha> && python3 -I <dir>/bench/scope_check.py check <role> --snapshot <dir> --sha <sha>
        The orchestrator keeps <sha> in its own context, so the originator can swap neither the snapshot nor the checker.
        After the originator returns. Exit 0 in scope, 1 violations (`SCOPE:<path> — why`), 2 usage error/tampering.

What counts as a change: tracked, untracked and gitignored files (except build output: target/, node_modules/,
test-results/, playwright-report/ at any depth; build/ and dist/ directly under a module), every file under .plumbline/,
every git ref (a commit on any branch), a new skip-worktree/assume-unchanged flag (it hides edits from git), any file of
the .agentic-sdlc folder ($AGENTIC_SDLC), and the test/coverage parts of any pom.xml. Pre-existing uncommitted work is in the snapshot and is not blamed.

Inside .plumbline/ the originator may only create or change: the --writable globs given at snapshot time (its artifact) and
`.plumbline/work/<name>/fixlog.md`. Input files there (story, facts, CI log, discovery, brief, feedback, benchmark reports)
are read-only. Outside .plumbline/, the role's allowed globs apply, and protected control files are denied (except Doc's
CLAUDE.md job). Writes outside the repository cannot be seen; Bash-capable roles are told not to make them.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gates" / "checks"))
import protected_paths  # noqa: E402

ANY_DEPTH = {"target", "node_modules", "__pycache__", "test-results", "playwright-report"}   # build output, any depth
MODULE_ROOT = {"build", "dist"}        # build output only directly under a module (frontend/dist, services/x/build)


def build_output(path):
    parts = path.split("/")
    if any(x in ANY_DEPTH for x in parts[:-1]) or path.endswith(".class"):
        return True
    if parts[0] in MODULE_ROOT and len(parts) > 1:      # build/ or dist/ of an app at the repository root
        return True
    root = 2 if parts[0] == "services" else 1
    return len(parts) > root + 1 and parts[root] in MODULE_ROOT


GRADLE_AND_WRAPPERS = {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew",
                       "gradlew.bat", "mvnw", "mvnw.cmd", "gradle.properties"}
ROLES = {   # (allowed globs outside .plumbline/, deny protected control files). @CODE, @TESTS, @DOCS: from the repo layout
    "pm": ([], True), "ba": ([], True), "arch": ([], True), "sm": ([], True), "onboard": ([], True),
    "dev": (["@CODE"], True),
    "qa": (["test-results/*", "playwright-report/*", "@TESTS"], True),
    "devops": (["@CODE", "docker/*", "k8s/*", "pom.xml", "**/Dockerfile*", "docker-compose*.yml", "docker-compose*.yaml"],
               True),
    "doc": (["@DOCS", "CLAUDE.md", "docs/*"], False),
}


def layout_globs():
    """Per-repo globs, computed at snapshot time from impact/layout.py (services/<name>, top-level modules, a root
    app, frontends) and stored in the integrity-checked snapshot."""
    sys.path.insert(0, str(ROOT / "impact"))
    import layout
    units = layout.units(Path("."))
    pre = lambda u: "" if u["path"] == "." else u["path"] + "/"
    fe = [u for u in units if u["kind"] == "frontend"]
    return {"@CODE": layout.code_globs(units),
            "@TESTS": [pre(u) + d for u in fe for d in ("tests/*", "e2e/*")],
            "@DOCS": [pre(u) + f for u in units for f in ("openapi.yaml", "openapi.yml")] + [layout.claude_md(u) for u in units]}


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "deleted"


BUNDLE = ("bench/scope_check.py", "gates/checks/protected_paths.py", "snapshot.json")


def bundle_sha(d):
    """One SHA-256 over the checker copy, its helper and the snapshot. The orchestrator keeps the printed value in its
    own context and re-computes it with sha256sum before running the copy, so none of the three can be swapped."""
    return hashlib.sha256(b"".join(Path(d, f).read_bytes() for f in BUNDLE)).hexdigest()


def guardrails_tree(root):
    """Hash of every file of the .agentic-sdlc folder, so a Bash-capable originator cannot edit the checkers."""
    root, h = Path(root), hashlib.sha256()
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root).parts
        if f.is_file() and ".git" not in rel and "__pycache__" not in rel:
            h.update("/".join(rel).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def state(guardrails):
    files = {}
    out = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "status",
                          "--porcelain", "-z", "-uall", "--ignored", "--no-renames"], capture_output=True).stdout
    for entry in out.split(b"\0"):
        if len(entry) < 4:
            continue
        path = entry[3:].decode("utf-8", "surrogateescape").rstrip("/")
        if path.startswith(".plumbline/") or build_output(path):
            continue
        files[path] = sha(Path(path))
    for f in Path(".plumbline").rglob("*") if Path(".plumbline").exists() else []:
        if f.is_symlink():
            files[str(f)] = "symlink:" + os.readlink(f)
        elif f.is_file():
            files[str(f)] = sha(f)
    # files git status would not show: skip-worktree / assume-unchanged flags
    hidden = sorted(l[2:] for l in git("ls-files", "-v").splitlines() if l[:1] == "S" or l[:1].islower())
    for h in hidden:                       # already-hidden files: compare their contents directly
        files[h] = sha(Path(h))
    refs = dict(l.split(" ", 1)[::-1] for l in git("for-each-ref", "--format=%(objectname) %(refname)").splitlines() if " " in l)
    return {"head": git("rev-parse", "HEAD").strip(), "refs": refs, "files": files, "hidden": hidden,
            "guardrails": guardrails_tree(guardrails)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "check"])
    ap.add_argument("role", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--role", dest="check_role", help="snapshot: print the ready-to-run CHECK command for this role")
    ap.add_argument("--writable", default="")
    ap.add_argument("--snapshot")
    ap.add_argument("--sha")
    a = ap.parse_args()
    if a.cmd == "snapshot":
        if not a.name or "/" in a.name:
            print("scope_check: --name is required and must not contain '/'", file=sys.stderr)
            return 2
        snap = {"name": a.name, "writable": a.writable.split(), "repo": os.getcwd(), "guardrails_root": str(ROOT),
                "layout": layout_globs(),
                **state(ROOT)}
        d = Path(tempfile.mkdtemp(prefix="plumbline-scope-"))
        (d / "snapshot.json").write_text(json.dumps(snap))
        # run `check` from this private copy, so an edit to the .agentic-sdlc folder cannot change the checker
        (d / "bench").mkdir(); (d / "gates" / "checks").mkdir(parents=True)
        shutil.copy2(ROOT / "bench" / "scope_check.py", d / "bench" / "scope_check.py")
        shutil.copy2(ROOT / "gates" / "checks" / "protected_paths.py", d / "gates" / "checks" / "protected_paths.py")
        sha_ = bundle_sha(d)
        print(f"SNAPSHOT {d} {sha_}")
        if a.check_role:
            # One portable line (no sha256sum/shasum differences between Linux and macOS): python -I verifies the sha of
            # the three files, then runs the private checker. Copy it as printed; never retype the sha.
            code = ("import hashlib,runpy,sys;d,s,r=sys.argv[1:4];"
                    "h=hashlib.sha256(b''.join(open(d+f,'rb').read() for f in "
                    "('/bench/scope_check.py','/gates/checks/protected_paths.py','/snapshot.json'))).hexdigest();"
                    "h==s or sys.exit('SCOPE:<checker> - snapshot or checker copy was modified');"
                    "sys.argv=[d+'/bench/scope_check.py','check',r,'--snapshot',d,'--sha',s];"
                    "runpy.run_path(sys.argv[0],run_name='__main__')")
            print(f'CHECK: python3 -I -c "{code}" {d} {sha_} {a.check_role}')
        return 0
    if a.role not in ROLES:
        print(f"scope_check: unknown role {a.role!r} (known: {', '.join(sorted(ROLES))})", file=sys.stderr)
        return 2
    if not (a.snapshot and a.sha and all(Path(a.snapshot, f).is_file() for f in BUNDLE)):
        print("scope_check: pass --snapshot DIR --sha SHA from the `snapshot` output", file=sys.stderr)
        return 2
    if bundle_sha(a.snapshot) != a.sha:
        print("SCOPE:<checker> — the snapshot or the checker copy was modified after it was taken; the attempt fails")
        return 1
    snap = json.loads(Path(a.snapshot, "snapshot.json").read_text())
    if os.path.realpath(snap["repo"]) != os.path.realpath(os.getcwd()):
        print(f"scope_check: run from the same repository the snapshot was taken in ({snap['repo']})", file=sys.stderr)
        return 2
    now = state(snap["guardrails_root"])
    changed = {p for p in set(now["files"]) | set(snap["files"]) if now["files"].get(p, "clean") != snap["files"].get(p, "clean")}
    bad = []
    if now["guardrails"] != snap["guardrails"]:
        bad.append("SCOPE:<agentic-sdlc> — the .agentic-sdlc folder (gates, bench, specs) was modified")
    for p in sorted(set(now["hidden"]) - set(snap["hidden"])):
        bad.append(f"SCOPE:{p} — marked skip-worktree/assume-unchanged, which hides edits from git")
    if now["head"] != snap["head"] or now["refs"] != snap["refs"]:
        moved = sorted(r for r in set(now["refs"]) | set(snap["refs"]) if now["refs"].get(r) != snap["refs"].get(r))
        bad.append(f"SCOPE:<git> — refs changed ({', '.join(moved) or 'HEAD'}); only the orchestrator commits")
        changed |= set(git("diff", "--name-only", f"{snap['head']}..{now['head']}").split()) if now["head"] != snap["head"] else set()
    allowed, deny_protected = ROLES[a.role]
    allowed = [g for x in allowed for g in (snap["layout"].get(x, []) if x.startswith("@") else [x])]
    own = [f".plumbline/work/{snap['name']}/fixlog.md"] + snap["writable"]
    for p in sorted(changed):
        if p.startswith(".plumbline/"):
            if not any(fnmatch.fnmatch(p, g) for g in own):
                bad.append(f"SCOPE:{p} — inside .plumbline/ the {a.role} originator may only write its artifact and fix log")
            continue
        ok = any(protected_paths.match(p, g) for g in allowed)
        if ok and (p.split("/")[-1] in GRADLE_AND_WRAPPERS or "/gradle/wrapper/" in "/" + p or "/.mvn/" in "/" + p):
            bad.append(f"SCOPE:{p} — Gradle build files and build wrappers can disable tests; only a human may change them")
            continue
        if ok and deny_protected and any(protected_paths.match(p, g) for g in protected_paths.PROTECTED):
            ok = False
        if ok and p.endswith("pom.xml"):
            old = git("show", f"{snap['head']}:{p}")
            new = Path(p).read_text() if Path(p).is_file() else ""
            if protected_paths.guarded_pom_parts(old) != protected_paths.guarded_pom_parts(new):
                bad.append(f"SCOPE:{p} — changes test/coverage configuration (surefire, failsafe, jacoco, skipTests)")
                continue
        if not ok:
            bad.append(f"SCOPE:{p} — outside what the {a.role} originator may change")
    for b in bad:
        print(b)
    print(f"scope check ({a.role}): {len(changed)} path(s) changed, {len(bad)} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
