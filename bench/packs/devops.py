"""DevOps benchmark — pipeline/infra changes and the CI result (devops-eval-loop Step C/D).
Judge keeps: is the fix the right one (root cause, not symptom), rollback and blast radius, security posture."""
import re
import shutil
import subprocess

import yaml

from common import UsageError, changed_lines, gh, git_ok_ref, read

SECRET = re.compile(r"""(?ix)(password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*["']?(?!\$\{|\$\(|<|\*{3})[A-Za-z0-9+/_\-!@#%^&]{8,}"""
                    r"""|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}""")


def run(r, ctx):
    repo = ctx.repo.path
    if not repo:
        raise UsageError("pass --repo")
    if ctx.base and not git_ok_ref(repo, ctx.base):
        raise UsageError(f"--base {ctx.base} is not a commit")
    touched = changed_lines(repo, ctx.base) if ctx.base else None
    wfs = sorted((repo / ".github/workflows").glob("*.y*ml"))
    bad_yaml, unpinned, floating, no_perm, pipe_sh, unverified, prt = [], [], [], [], [], [], []
    for f in wfs:
        rel = str(f.relative_to(repo))
        try:
            doc = yaml.safe_load(read(f)) or {}
        except yaml.YAMLError as e:
            bad_yaml.append(f"{rel}: {str(e).splitlines()[0]}")
            continue
        if "permissions" not in doc and not any("permissions" in (j or {}) for j in (doc.get("jobs") or {}).values()):
            no_perm.append(rel)
        on = doc.get(True, doc.get("on", {}))
        triggers = on if isinstance(on, (dict, list)) else [on]
        for job in (doc.get("jobs") or {}).values():
            steps = (job or {}).get("steps") or []
            checks_out_head = False
            for st in steps:
                u = st.get("uses")
                if u and not u.startswith(("./", "docker://")):
                    if "@" not in u:
                        unpinned.append(f"{rel}: {u}")
                    else:
                        ref = u.split("@", 1)[1]
                        if ref in ("main", "master", "latest", "HEAD", "develop"):
                            unpinned.append(f"{rel}: {u}")
                        elif not re.fullmatch(r"[0-9a-f]{40}", ref):
                            floating.append(f"{rel}: {u}")
                    if u.startswith("actions/checkout") and "head" in str((st.get("with") or {}).get("ref", "")):
                        checks_out_head = True
                run_ = st.get("run") or ""
                if re.search(r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b", run_):
                    pipe_sh.append(f"{rel}: {run_.strip().splitlines()[0][:100]}")
                if re.search(r"(curl|wget)\b[^\n]*(-o|-O|--output)\s", run_) and not re.search(r"sha256sum|shasum -a 256|sha512sum", run_):
                    unverified.append(f"{rel}: {run_.strip().splitlines()[0][:100]}")
                if checks_out_head and "pull_request_target" in str(triggers) and re.search(
                        r"\b(mvn|npm|yarn|pnpm|gradle|make|pip install -e|\./)", run_):
                    prt.append(f"{rel}: runs `{run_.strip().splitlines()[0][:60]}` after checking out the PR head")
    r.add("DO-1", "Workflows parse as YAML", not bad_yaml, f"{len(wfs)} workflows", bad_yaml)
    r.add("DO-2", "Actions pinned (no @main/@master/@latest or missing ref)", not unpinned, f"{len(unpinned)} unpinned", unpinned)
    r.add("DO-3", "Actions pinned to a commit SHA", not floating, f"{len(floating)} pinned to a tag only", floating, warn=True)
    r.add("DO-4", "No download piped straight into a shell", not pipe_sh, f"{len(pipe_sh)} found", pipe_sh)
    r.add("DO-5", "Downloaded files are checksum-verified", not unverified, f"{len(unverified)} unverified", unverified)
    r.add("DO-6", "Workflows declare least-privilege `permissions:`", not no_perm, f"{len(no_perm)} without", no_perm, warn=True)
    r.add("DO-7", "pull_request_target never executes PR code", not prt, f"{len(prt)} risky", prt)

    leaks, old_leaks = [], []
    for pat in (".github/workflows/*.y*ml", "**/Dockerfile*", "k8s/**/*.y*ml", "docker-compose*.y*ml", "**/application*.y*ml"):
        for f in repo.glob(pat):
            if "node_modules" in f.parts or "target" in f.parts:
                continue
            for i, l in enumerate(read(f).splitlines(), 1):
                if SECRET.search(l) and "secrets." not in l:
                    rel = str(f.relative_to(repo))
                    (leaks if touched is None or i in touched.get(rel, set()) else old_leaks).append(f"{rel}:{i}")
    scope = "on lines this change adds" if touched is not None else "in the repo (pass --base to judge only this change)"
    r.add("DO-8", f"No plaintext secrets {scope}", not leaks, f"{len(leaks)} suspicious lines", leaks)
    if touched is not None:
        r.add("DO-8b", "Pre-existing plaintext secrets (debt, not caused by this change)", not old_leaks,
              f"{len(old_leaks)} lines", old_leaks, warn=True)

    latest = []
    for f in repo.glob("**/Dockerfile*"):
        if "node_modules" in f.parts:
            continue
        for l in read(f).splitlines():
            m = re.match(r"\s*FROM\s+(\S+)", l, re.I)
            if m and m.group(1).lower() != "scratch" and (":" not in m.group(1).split("/")[-1] or m.group(1).endswith(":latest")) \
                    and "@sha256:" not in m.group(1) and not m.group(1).startswith("$"):
                latest.append(f"{f.relative_to(repo)}: FROM {m.group(1)}")
    r.add("DO-9", "Docker base images pinned (no :latest / no tag)", not latest, f"{len(latest)} floating", latest)

    if shutil.which("actionlint"):
        a = subprocess.run(["actionlint"], cwd=repo, capture_output=True, text=True)
        r.add("DO-10", "actionlint clean", a.returncode == 0, f"exit {a.returncode}", a.stdout.splitlines()[:15])
    else:
        r.skip("DO-10", "actionlint clean", "actionlint not installed")
    if ctx.branch:
        runs = gh("run", "list", "--branch", ctx.branch, "--limit", "1", "--json", "conclusion,status,headSha,name")
        if runs is None:
            r.skip("DO-11", "Latest CI run on the branch is green", "gh unavailable or not authenticated")
        else:
            last = runs[0] if runs else {}
            r.add("DO-11", "Latest CI run on the branch is green", last.get("conclusion") == "success",
                  f"{last.get('name')} {last.get('status')}/{last.get('conclusion')} @ {str(last.get('headSha'))[:8]}" if last else "no runs")
    else:
        r.skip("DO-11", "Latest CI run green", "pass --branch")
