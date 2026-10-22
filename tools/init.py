#!/usr/bin/env python3
"""Plumbline init — set up (or check, or upgrade) a repository in one step.

  python3 .plumbline/init.py                    detect → project.yaml → install → baseline → prerequisites → doctor
  python3 .plumbline/init.py --jira KEY        set the JIRA project key (and Confluence space; --confluence to differ)
  python3 .plumbline/init.py --domain broker-dealer   same, with the broker-dealer example domain pack and its gates
  python3 .plumbline/init.py --doctor           report only: what the framework can and cannot see (no writes)
  python3 .plumbline/init.py --check            CI: exit 1 if generated files, project.yaml or baseline are stale
  python3 .plumbline/init.py --upgrade FILE.tar.gz   replace the framework, keep project.yaml and the baseline
  python3 .plumbline/init.py --ci               also install the CI workflows (.github/workflows/plumbline-*.yml)
  python3 .plumbline/init.py --uninstall --yes  remove every Plumbline file (the project's CLAUDE.md files stay)

Footprint: everything lives in .plumbline/ (framework, project.yaml, baseline, loop working files in run/, ignored by
.plumbline/.gitignore). Outside it, only the entry files the tools require, all named plumbline-*:
.claude/commands, .claude/agents, .github/prompts, .github/agents — and .github/workflows only with --ci.
The root .gitignore is not touched. An existing project.yaml is never overwritten.
"""
import argparse
import json
import re
import shutil
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
if sys.platform == "win32" and not sys.flags.utf8_mode and __name__ == "__main__":   # Windows: UTF-8 like macOS/Linux
    import subprocess as _sp
    sys.exit(_sp.call([sys.executable, "-X", "utf8", *(["-I"] if sys.flags.isolated else []), *sys.argv],
                      env={**__import__("os").environ, "PYTHONUTF8": "1"}))

G = Path(__file__).resolve().parent            # the .plumbline folder
REPO = G.parent
sys.path.insert(0, str(G / "impact"))
try:
    import layout  # noqa: E402
except ImportError:          # only init.py present (first step of an --upgrade from an older layout)
    layout = None

PROJECT = G / "project.yaml"
BASELINE = G / "gates" / "baseline.json"
KEEP_ON_UPGRADE = ("project.yaml", "gates/baseline.json")
INSTALL = [   # (generated source in .plumbline, destination in the repo)
    ("dist/claude-code/.claude/commands", ".claude/commands"),
    ("dist/claude-code/.claude/agents", ".claude/agents"),
    ("dist/copilot/.github/prompts", ".github/prompts"),
    ("dist/copilot/.github/agents", ".github/agents"),
]
WORKFLOWS = [("gates/ci/guardrails.yml", "plumbline-guardrails.yml"), ("gates/ci/critic.yml", "plumbline-critic.yml"),
             ("gates/ci/impact-cache.yml", "plumbline-impact-cache.yml")]
LEGACY = REPO / ".agentic-sdlc"                 # the folder name before 1.10
DOMAINS = {   # domain pack + gate selection
    "none": {"domain_pack": "none", "gates": {"semgrep": ["java-generic.yml"], "checks": ["structure_check"]}},
    "broker-dealer": {"domain_pack": ".plumbline/packs/domain-rules/rules.yaml",
                      "gates": {"semgrep": ["java-generic.yml", "oms-rules.yml", "oms-domain-rules.yml"],
                                "checks": ["structure_check", "domain_check"]}},
}
BD_PACK = DOMAINS["broker-dealer"]["domain_pack"]
# Project settings rendered into the installed agent files ({{TOKEN}} in dist/). Edit them in project.yaml, re-run init.
SETTINGS = {   # key in project.yaml → (token, comment)
    "jira_project": ("JIRA_KEY", "JIRA project key the loops read and write (tickets look like <key>-123)"),
    "confluence_space": ("CONFLUENCE_SPACE", "Confluence space for test plans, reports and runbooks"),
    "api_url": ("API_URL", "where QA reaches the running backend (or its gateway)"),
    "frontend_url": ("FRONTEND_URL", "where QA reaches the running frontend"),
    "login_path": ("LOGIN_PATH", "QA login endpoint for the demo user (POST username/password, returns a token)"),
}
FRONTEND_PORT = {"angular": 4200, "next": 3000, "vue": 5173, "react": 5173, "svelte": 5173}


def sh(*cmd, cwd=REPO, timeout=600):
    env = dict(os.environ, SEMGREP_ENABLE_VERSION_CHECK="0", SEMGREP_SEND_METRICS="off")
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError:
        return 127, f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, f"{cmd[0]}: timed out after {timeout}s"
    return r.returncode, (r.stdout + r.stderr).strip()


def say(tag, msg):
    print(f"{tag:6} {msg}")


# ───────────── detect ─────────────

def java_version(unit_dir: Path):
    pom = unit_dir / "pom.xml"
    if pom.is_file():
        t = pom.read_text(errors="replace")
        for pat in (r"<maven\.compiler\.release>(\d+)<", r"<release>(\d+)<", r"<java\.version>(\d+)<",
                    r"<maven\.compiler\.source>(?:1\.)?(\d+)<"):
            m = re.search(pat, t)
            if m:
                return int(m.group(1))
    for g in ("build.gradle", "build.gradle.kts"):
        f = unit_dir / g
        if f.is_file():
            t = f.read_text(errors="replace")
            m = re.search(r"JavaLanguageVersion\.of\((\d+)\)", t) or re.search(r"sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?(?:1[._])?(\d+)", t)
            if m:
                return int(m.group(1))
    return None


def frontend_framework(unit_dir: Path):
    pj = unit_dir / "package.json"
    if not pj.is_file():
        return None
    try:
        d = json.loads(pj.read_text())
    except ValueError:
        return "unknown"
    deps = {**(d.get("dependencies") or {}), **(d.get("devDependencies") or {})}
    for key, name in (("@angular/core", "angular"), ("next", "next"), ("react", "react"), ("vue", "vue"), ("svelte", "svelte")):
        if key in deps:
            return f"{name} {str(deps[key]).lstrip('^~')}"
    return "unknown"


def base_branch():
    rc, out = sh("git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if rc == 0 and out:
        return out.split("/", 1)[-1]
    for b in ("develop", "main", "master"):
        if sh("git", "rev-parse", "--verify", "-q", b)[0] == 0 or sh("git", "rev-parse", "--verify", "-q", f"origin/{b}")[0] == 0:
            return b
    return "main"


def detect():
    units = layout.units(REPO)
    for u in units:
        d = REPO / u["path"]
        if u["kind"] == "service":
            u["java"] = java_version(d) or java_version(REPO)      # modules usually inherit it from the parent pom
        else:
            u["framework"] = frontend_framework(d)
    return units


# ───────────── project.yaml ─────────────

def write_project(units, domain):
    if PROJECT.is_file():
        say("keep", f"{PROJECT.relative_to(REPO).as_posix()} exists — not changed")
        return False
    d = DOMAINS[domain]
    lines = ["# Plumbline project configuration — written by init.py, edited by people (protected path).",
             "units:"]
    for u in units:
        lines.append(f"  - {{name: {u['name']}, path: {u['path']}, kind: {u['kind']}}}")
    lines += ["", f"base_branch: {base_branch()}", "",
              "# Domain rule pack the judge applies; `none` for a repository without one.",
              f"domain_pack: {d['domain_pack']}"]
    lines += ["", "# Gate selection: Semgrep packs under .plumbline/gates/semgrep/, checks under gates/checks/.",
              "gates:", f"  semgrep: [{', '.join(d['gates']['semgrep'])}]", f"  checks: [{', '.join(d['gates']['checks'])}]"]
    PROJECT.write_text("\n".join(lines) + "\n", newline="\n")
    say("write", f"{PROJECT.relative_to(REPO).as_posix()} ({len(units)} units, domain {domain})")
    return True


def setting_defaults(units, jira=None, confluence=None):
    import depmap
    import contextlib
    import io
    with contextlib.redirect_stderr(io.StringIO()):
        svc = depmap.build(REPO, None, None)["services"]
    backends = [u for u in units if u["kind"] == "service"]
    gw = next((u for u in backends if "gateway" in u["name"]), backends[0] if backends else None)
    port = (svc.get(gw["name"], {}).get("port") if gw else None) or 8080
    fe = next((u for u in units if u["kind"] != "service"), None)
    fport = FRONTEND_PORT.get(((fe or {}).get("framework") or "").split(" ")[0], 5173)
    old = legacy_jira()
    return {"jira_project": jira or old or "PROJ", "confluence_space": confluence or jira or old or "PROJ",
            "api_url": f"http://localhost:{port}", "frontend_url": f"http://localhost:{fport}",
            "login_path": "/api/v1/auth/login"}


def legacy_jira():
    """Installs before 1.11 had the JIRA key SCRUM written into the agent files: keep it on upgrade."""
    for gd in (".claude/commands", ".github/prompts"):
        for f in (REPO / gd).glob("*.md") if (REPO / gd).is_dir() else []:
            if (f.name.startswith("plumbline-") or "eval-loop" in f.name) and "SCRUM-{n}" in f.read_text(errors="replace"):
                return "SCRUM"
    return None


def ensure_settings(units, jira=None, confluence=None):
    """Add missing settings (and, for a pre-1.11 broker-dealer project.yaml, its explicit gate list) to project.yaml,
    keeping everything people wrote. --jira/--confluence replace the stored value."""
    cfg = layout.project(config=PROJECT) or {}
    text = PROJECT.read_text()
    add, changed = [], []
    if "gates" not in cfg:                          # before 1.11 a missing `gates:` meant every pack (broker-dealer)
        d = DOMAINS["broker-dealer" if cfg.get("domain_pack") == BD_PACK else "none"]["gates"]
        add += ["", "# Gate selection: Semgrep packs under .plumbline/gates/semgrep/, checks under gates/checks/.",
                "gates:", f"  semgrep: [{', '.join(d['semgrep'])}]", f"  checks: [{', '.join(d['checks'])}]"]
    if jira and not confluence and str(cfg.get("confluence_space", "PROJ")) == "PROJ":
        confluence = jira                           # the space was never set: follow the JIRA key
    wanted = {"jira_project": jira, "confluence_space": confluence}
    for k, v in wanted.items():
        if v and k in cfg and str(cfg[k]) != v:
            text = re.sub(rf"(?m)^{k}:.*$", f"{k}: {v}", text)
            changed.append(f"{k}={v}")
    missing = [k for k in SETTINGS if k not in cfg]
    if missing:
        dflt = setting_defaults(units, jira, confluence)
        add += ["", "# Project settings, rendered into the installed agent files. Edit, then re-run init.py."]
        for k in missing:
            add.append(f"{k}: {dflt[k]}{' ' * max(1, 34 - len(k) - len(str(dflt[k])))}# {SETTINGS[k][1]}")
    if add or changed:
        PROJECT.write_text(text.rstrip("\n") + "\n" + ("\n".join(add) + "\n" if add else ""), newline="\n")
        say("write", f"{PROJECT.relative_to(REPO).as_posix()}: " + ", ".join(
            (["gate selection"] if "gates" not in cfg else []) + [f"{k}" for k in missing] + changed) + " added/updated")


def settings():
    cfg = layout.project(config=PROJECT) or {}
    return {tok: str(cfg.get(k, "PROJ" if k in ("jira_project", "confluence_space") else "")) for k, (tok, _c) in SETTINGS.items()}


def render(src):
    text = src.read_text()
    if src.suffix == ".md":
        for tok, v in settings().items():
            text = text.replace("{{" + tok + "}}", v)
    return text


def same(src, dst):
    # compare without line endings: a Windows checkout (core.autocrlf) has CRLF where the framework has LF
    return dst.exists() and dst.read_bytes().decode("utf-8", "replace").replace("\r", "") == render(src).replace("\r", "")


# ───────────── install generated files ─────────────

def ci_installed():
    return any((REPO / ".github" / "workflows" / name).exists() for _s, name in WORKFLOWS)


def pairs(ci=None):
    ci = ci_installed() if ci is None else ci
    for src, dst in INSTALL:
        for f in sorted((G / src).glob("*.md")):
            yield f, REPO / dst / f.name
    if ci:
        for src, name in WORKFLOWS:
            yield G / src, REPO / ".github" / "workflows" / name


GENERATED_DIRS = [".claude/commands", ".claude/agents", ".github/prompts", ".github/agents", ".github/workflows"]


def leftovers():
    """Plumbline files from older installs that the current version no longer generates (old command, agent or
    workflow names). Only files that are recognisably ours: plumbline-* names, or old loop/agent names, or
    workflows that run the framework."""
    expected = {d for _s, d in pairs(ci=True)}
    out = []
    for gd in GENERATED_DIRS:
        for f in sorted((REPO / gd).glob("*")) if (REPO / gd).is_dir() else []:
            if f in expected or not f.is_file():
                continue
            text = f.read_text(errors="replace")
            framework = re.search(r"\.agentic-sdlc|\.guardrails|GUARDRAILS|\.plumbline/|eval loop|ORIGINATOR", text, re.I)
            ours = f.name.startswith("plumbline-") or (framework and re.search(
                r"-originator(\.agent)?\.md$|-critic(\.agent|\.prompt)?\.(md|yml)$|eval-loop(\.prompt)?\.md$|"
                r"^jira-ping(\.prompt)?\.md$|\.ya?ml$", f.name))
            if ours:
                out.append(f.relative_to(REPO).as_posix())
    return out


def install(ci=False):
    n = 0
    for s_, d in pairs(ci=ci or None):
        d.parent.mkdir(parents=True, exist_ok=True)
        if not same(s_, d):
            d.write_text(render(s_), newline="\n")
            n += 1
    for f in leftovers():
        say("warn", f"left over from an older install (remove it): git rm {f}")
    say("write", f"entry files (plumbline-*): {n} updated, {len(list(pairs())) - n} already current"
                 + ("" if ci_installed() else "; CI workflows not installed (add with --ci)"))


def stale_generated():
    return [d.relative_to(REPO).as_posix() for s, d in pairs() if not same(s, d)]


# ───────────── prerequisites ─────────────

def prerequisites(units):
    probs = []
    say("ok" if sys.version_info >= (3, 10) else "MISS", f"python {sys.version.split()[0]} (>= 3.10)")
    if sys.version_info < (3, 10):
        probs.append("python3 >= 3.10")
    if sys.platform == "win32":                    # the agents run bash commands that call python3
        if not shutil.which("bash"):
            say("MISS", "bash — install Git for Windows and use Git Bash as the agent terminal (or work in WSL)")
            probs.append("bash")
        if not shutil.which("python3"):
            say("MISS", "python3 not on PATH — in Git Bash run: "
                        "cp \"$(command -v python)\" \"$(dirname \"$(command -v python)\")/python3.exe\"")
            probs.append("python3")
    try:
        import yaml  # noqa: F401
        say("ok", "PyYAML")
    except ImportError:
        say("MISS", "PyYAML — pip install -r .plumbline/requirements.txt")
        probs.append("PyYAML")
    want = re.search(r"semgrep==([\d.]+)", (G / "requirements.txt").read_text())
    rc, out = sh("semgrep", "--version", timeout=60)
    if rc != 0:
        say("MISS", "Semgrep — gates cannot run (pip install -r .plumbline/requirements.txt)")
        probs.append("semgrep")
    else:
        say("ok" if not want or want.group(1) in out else "warn", f"semgrep {out.splitlines()[-1]}"
            + ("" if not want or want.group(1) in out else f" (pinned {want.group(1)})"))
    javas = sorted({u.get("java") for u in units if u.get("java")})
    if javas:
        rc, out = sh("java", "-version", timeout=60)
        m = re.search(r'version "(?:1\.)?(\d+)', out)
        have = int(m.group(1)) if m else None
        for v in javas:
            if have == v:
                say("ok", f"JDK {have} (build declares {v})")
            else:
                say("warn", f"JDK {have or 'missing'}, build declares {v}: select it, e.g. "
                            f"export JAVA_HOME=$(/usr/libexec/java_home -v {v})  — onboarding works without it; Dev/QA need it")
        for w in ("mvnw", "gradlew"):
            f = REPO / w
            if f.exists():
                raw = f.read_bytes()
                if b"\r\n" in raw:
                    say("warn", f"{w} has Windows line endings (CRLF): it will not run on macOS/Linux")
                elif not (f.stat().st_mode & 0o111):
                    say("warn", f"{w} is not executable: chmod +x {w}")
    if any(u["kind"] == "frontend" for u in units):
        rc, out = sh("node", "--version", timeout=60)
        say("ok" if rc == 0 else "warn", f"node {out if rc == 0 else 'missing (frontend tests and coverage need it)'}")
    rc, _ = sh("git", "rev-parse", "--git-dir")
    if rc != 0:
        say("MISS", "not a git repository")
        probs.append("git")
    return probs


# ───────────── baseline ─────────────

def foreign_baseline():
    """Releases before 1.11 shipped the broker-dealer reference repo's baseline; every repository needs its own."""
    cfg = layout.project(config=PROJECT) or {}
    return BASELINE.is_file() and "services/order-service/" in BASELINE.read_text() and \
        cfg.get("domain_pack", "none") != BD_PACK


def baseline(force=False):
    foreign = foreign_baseline()
    if BASELINE.is_file() and not (force or foreign):
        say("keep", f"{BASELINE.relative_to(REPO).as_posix()} exists — not changed (--rebaseline to rebuild)")
        return
    if sh("semgrep", "--version", timeout=60)[0] != 0:
        if foreign:
            BASELINE.unlink()
            say("remove", "the baseline an older release shipped (another repository's findings)")
        say("skip", "baseline not written: Semgrep is missing — install it, then run: python3 .plumbline/init.py --rebaseline")
        return
    rc, out = sh(sys.executable, str(G / "gates" / "run_gates.py"), ".", "--write-baseline", str(BASELINE))
    say("write" if rc == 0 else "FAIL", f"gates baseline for this repository: {out.splitlines()[-1] if out else rc}")


# ───────────── doctor ─────────────

def doctor(units):
    import contextlib
    import io
    import depmap
    with contextlib.redirect_stderr(io.StringIO()):
        dm = depmap.build(REPO, None, None)
    cfg = layout.project(config=PROJECT)
    print("\nPLUMBLINE DOCTOR — what the framework can see")
    print(f"  repository   : {REPO.name}   base branch: {cfg.get('base_branch') or base_branch()}   "
          f"domain pack: {cfg.get('domain_pack', 'none')}")
    s = settings()
    print(f"  settings     : JIRA {s['JIRA_KEY']}   Confluence {s['CONFLUENCE_SPACE']}   API {s['API_URL']}   "
          f"frontend {s['FRONTEND_URL']}   login {s['LOGIN_PATH']}")
    warn = []
    for u in units:
        e = dm["services"].get(u["name"]) or next((x for x in dm["services"].values() if x["path"] == u["path"]), {})
        cm = layout.claude_md(u)
        has_cm = (REPO / cm).is_file()
        if u["kind"] == "service":
            print(f"  [backend ] {u['name']:28} {u['path']:22} {u.get('build') or '?':6} Java {u.get('java') or '?':<3} "
                  f"port {e.get('port') or '?':<5} endpoints {len(e.get('provides', [])):<4} kafka {len(e.get('kafka', [])):<3}"
                  f" CLAUDE.md {'yes' if has_cm else 'no'} ({cm})")
            if not e.get("provides"):
                warn.append(f"{u['name']}: no endpoints found — check the controller layout")
        else:
            unres = e.get("unresolved", [])
            calls = len(e.get("calls", []))
            print(f"  [frontend] {u['name']:28} {u['path']:22} {u.get('framework') or '?':14} API calls {calls:<4} "
                  f"unresolved {len(unres):<3} CLAUDE.md {'yes' if has_cm else 'no'} ({cm})")
            if unres:
                warn.append(f"{u['name']}: {len(unres)} call(s) whose URL could not be resolved, e.g. {unres[:3]}")
    fe = {n for n, x in dm["services"].items() if x.get("kind") == "frontend"}
    unmatched = sorted({e["path"] for e in dm["rest_edges"] if not e.get("to") and e["from"] in fe})
    other = sorted({e["path"] for e in dm["rest_edges"] if not e.get("to") and e["from"] not in fe})
    print(f"  links        : {len([e for e in dm['rest_edges'] if e.get('to')])} calls matched to an endpoint; "
          f"{len(unmatched)} frontend call(s) with no endpoint; {len(other)} backend path literal(s) with no endpoint "
          f"(often prefixes in filters — informational)")
    if unmatched:
        warn.append(f"{len(unmatched)} frontend call(s) have no matching endpoint (drift or dead code), e.g. {unmatched[:4]}")
    root_cm = REPO / "CLAUDE.md"
    print(f"  root CLAUDE.md (master): {'present' if root_cm.is_file() else 'missing'}"
          f"{' — has solution block' if root_cm.is_file() and 'plumbline:begin solution' in root_cm.read_text(errors='replace') else ''}")
    g = (cfg.get("gates") or {})
    print(f"  gates        : semgrep {g.get('semgrep', ['java-generic.yml'])}  checks {g.get('checks', ['structure_check'])}  "
          f"baseline {'from another repository — rebuild: init.py --rebaseline' if foreign_baseline() else ('present' if BASELINE.is_file() else 'missing — install Semgrep, then init.py --rebaseline')}")
    if s["JIRA_KEY"] == "PROJ":
        warn.append("JIRA project key not set: edit jira_project (and confluence_space) in .plumbline/project.yaml, "
                    "or re-run init.py --jira <KEY>")
    stale = stale_generated()
    if stale:
        warn.append(f"{len(stale)} generated agent file(s) missing or stale — run init.py")
    if warn:
        print("  attention    :")
        for w in warn:
            print(f"    - {w}")
    else:
        print("  attention    : none")
    print()


# ───────────── check / upgrade ─────────────

def check():
    bad = []
    if not PROJECT.is_file():
        bad.append("project.yaml missing — run init.py")
    old_files = leftovers()
    if old_files:
        bad.append(f"files left over from an older install: {old_files[:5]}{' …' if len(old_files) > 5 else ''}")
    stale = stale_generated()
    if stale:
        bad.append(f"generated files stale or missing: {stale[:5]}{' …' if len(stale) > 5 else ''}")
    if PROJECT.is_file():
        try:
            declared = {(u["name"], u["path"]) for u in layout.units(REPO)}
        except SystemExit as e:
            bad.append(f"project.yaml invalid: {e}")
            declared = set()
        detected = {(u["path"]) for u in layout.units(REPO, config=str(G / "__none__.yaml"))}
        missing = sorted(detected - {p for _n, p in declared})
        if missing:
            bad.append(f"units detected but not declared in project.yaml: {missing}")
    if not BASELINE.is_file():
        bad.append("gates baseline missing (install Semgrep, then: python3 .plumbline/init.py --rebaseline)")
    elif foreign_baseline():
        bad.append("gates baseline belongs to another repository (python3 .plumbline/init.py --rebaseline)")
    for b in bad:
        say("FAIL", b)
    say("ok" if not bad else "FAIL", "plumbline check")
    return 1 if bad else 0


def upgrade(tarball, passthrough=()):
    stage = G.with_name(".plumbline.new")
    shutil.rmtree(stage, ignore_errors=True)
    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(tarball) as tf:
            members = [m for m in tf.getmembers() if m.name.startswith(".plumbline/") and ".." not in m.name.split("/")
                       and (m.isreg() or m.isdir())]
            for m in members:                       # plain permissions only (no setuid/setgid/sticky)
                m.mode = 0o755 if m.isdir() or m.mode & 0o111 else 0o644
            try:
                tf.extractall(td, members=members, filter="data")
            except TypeError:                       # Python without extraction filters: members are already vetted
                tf.extractall(td, members=members)
        new = Path(td) / ".plumbline"
        if not (new / "VERSION").is_file() or not (new / "init.py").is_file():
            raise SystemExit("upgrade: the tarball has no .plumbline/VERSION and init.py")
        for k in KEEP_ON_UPGRADE:                   # the tarball never brings its own project config or baseline
            (new / k).unlink(missing_ok=True)
        shutil.copytree(new, stage)
    for k in KEEP_ON_UPGRADE:
        if (G / k).is_file():
            (stage / k).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(G / k, stage / k)
    for d, dst in (("run", "run"), ("review", "run/review"), ("work", "run/work")):   # loop working files survive
        if (G / d).is_dir() and not (stage / dst).exists():
            (stage / dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(G / d, stage / dst)
    old_v = (G / "VERSION").read_text().strip() if (G / "VERSION").is_file() else "?"
    retired = G.with_name(".plumbline.old")
    shutil.rmtree(retired, ignore_errors=True)
    G.rename(retired)                               # swap: the old framework stays intact until the new one is in place
    try:
        stage.rename(G)
    except OSError:
        retired.rename(G)                           # put the old framework back
        raise
    shutil.rmtree(retired, ignore_errors=True)
    kept = [k for k in KEEP_ON_UPGRADE if (G / k).is_file()]
    say("write", f"framework {old_v} → {(G / 'VERSION').read_text().strip()} (kept: {', '.join(kept) or 'nothing'})")
    return subprocess.run([sys.executable, str(G / "init.py"), *passthrough]).returncode   # keeps this repo's baseline; replaces only the shipped broker-dealer one


def uninstall(yes):
    files = [d for _s, d in pairs(ci=True) if d.exists()] + [REPO / f for f in leftovers()]
    files = sorted(set(files))
    print("Plumbline uninstall would remove:")
    for f in files:
        print(f"  {f.relative_to(REPO).as_posix()}")
    print(f"  {G.relative_to(REPO).as_posix()}/  (framework, project.yaml, baseline, loop working files)")
    print("Kept: the project's CLAUDE.md files (they are project documentation).")
    if not yes:
        print("Nothing removed. Re-run with --yes to remove.")
        return 0
    for f in files:
        f.unlink(missing_ok=True)
    for gd in GENERATED_DIRS:
        d = REPO / gd
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    shutil.rmtree(G)
    print("Removed. Commit the deletions.")
    return 0


def migrate_legacy():
    """1.9 kept the framework in .agentic-sdlc/ and loop files in .plumbline/{review,work}: move them into place."""
    moved = []
    for old in ("review", "work"):
        if (G / old).is_dir():
            dst = G / "run" / old
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                (G / old).rename(dst)
                moved.append(f".plumbline/{old}/ → .plumbline/run/{old}/")
    if LEGACY.is_dir():
        for k in KEEP_ON_UPGRADE:
            if (LEGACY / k).is_file() and not (G / k).is_file():
                (G / k).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LEGACY / k, G / k)
                moved.append(f".agentic-sdlc/{k} → .plumbline/{k}")
        if PROJECT.is_file():
            PROJECT.write_text(PROJECT.read_text().replace(".agentic-sdlc/", ".plumbline/"), newline="\n")
        shutil.rmtree(LEGACY)
        moved.append("removed .agentic-sdlc/ (replaced by .plumbline/)")
    gi = REPO / ".gitignore"
    if gi.is_file():                                # 1.9 added ".plumbline/" to the root .gitignore: it would now hide
        text = gi.read_text()                       # the framework itself, so take our line out again
        new = re.sub(r"(?m)^\.plumbline/\s*\n?", "", text)
        if new != text:
            gi.write_text(new, newline="\n")
            moved.append("root .gitignore: removed the '.plumbline/' line an older install added "
                         "(.plumbline/.gitignore now ignores only run/)")
    for m in moved:
        say("move", m)


# ───────────── main ─────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", choices=sorted(DOMAINS), default="none")
    ap.add_argument("--jira", metavar="KEY", help="JIRA project key (written to project.yaml)")
    ap.add_argument("--confluence", metavar="SPACE", help="Confluence space key (default: the JIRA key)")
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--upgrade", metavar="TARBALL")
    ap.add_argument("--rebaseline", action="store_true")
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--ci", action="store_true", help="also install the CI workflows")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.upgrade:
        return upgrade(a.upgrade, [*(["--jira", a.jira] if a.jira else []), *(["--confluence", a.confluence] if a.confluence else []),
                                   *(["--ci"] if a.ci else [])])
    if layout is None:
        raise SystemExit("init: .plumbline/ is incomplete; run: python3 .plumbline/init.py --upgrade <plumbline tarball>")
    if a.uninstall:
        return uninstall(a.yes)
    print(f"Plumbline {(G / 'VERSION').read_text().strip()} — {REPO}")
    if not a.doctor:
        migrate_legacy()                      # 1.9 layout first: its project.yaml may declare the units
    units = detect()
    if not units:
        say("FAIL", "no units found (services/<name>/, top-level modules, an app at the root, or a frontend). "
                    "Declare them in .plumbline/project.yaml — see project.yaml.example")
        return 1
    if not a.doctor:
        write_project(units, a.domain)
        units = detect()                      # names/paths as declared
        ensure_settings(units, a.jira, a.confluence)
        install(a.ci)
    print()
    probs = prerequisites(units)
    if not a.doctor and not a.no_baseline:
        baseline(a.rebaseline)
    doctor(units)
    if not a.doctor:
        print("Next: commit .plumbline/ and the plumbline-* entry files, add CODEOWNERS for them, then run "
              "/plumbline-onboard service:all in Claude Code or Copilot.")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
