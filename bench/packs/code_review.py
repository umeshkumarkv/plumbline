"""Code-review benchmark — run in the pinned review worktree (code-review Phase 0) at REVIEWED_SHA.
Everything the dev benchmark measures, plus: protected paths, PR CI status on the reviewed head.
Judge keeps: the 12-category audit for what the gates cannot see, and whether prior findings are resolved."""
import os
import subprocess
import sys

from common import ROOT, gh
from packs import dev


def run(r, ctx):
    dev.run(r, ctx)
    repo = ctx.repo.path
    if not repo:
        return
    p = subprocess.run([sys.executable, str(ROOT / "gates/checks/protected_paths.py"), ctx.base, "HEAD"], cwd=repo,
                       capture_output=True, text=True, env={**os.environ, "PLUMBLINE_POLICY_PR": os.environ.get("PLUMBLINE_POLICY_PR", "0")})
    r.add("CR-1", "PR does not touch the controls that judge it (protected paths)", p.returncode == 0,
          p.stdout.strip().splitlines()[-1] if p.stdout.strip() else f"exit {p.returncode}",
          [l for l in p.stdout.splitlines() if l.startswith("PROTECTED")])
    if ctx.pr:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
        runs = gh("api", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs", "--jq", "[.check_runs[]|{name,conclusion,status}]")
        if runs is None:
            r.skip("CR-2", "CI checks green on the reviewed head", "gh unavailable or not authenticated")
        else:
            bad = [f"{x['name']}: {x['conclusion'] or x['status']}" for x in runs
                   if x["name"] != "plumbline/code-review" and x["conclusion"] not in ("success", "skipped", "neutral")]
            r.add("CR-2", "CI checks green on the reviewed head", bool(runs) and not bad,
                  f"{len(runs)} checks on {sha[:8]}" + (f", not green: {bad}" if bad else ""), bad)
