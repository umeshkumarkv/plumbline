#!/usr/bin/env python3
"""Self-test for the orchestrator / originator split (v1.3):
  1. every originator agent is least-privilege (no MCP, no web, no Agent tool; Bash only for dev, qa, devops)
  2. every Claude command hands Stage 1 to its agent and keeps no originator work inline; Copilot keeps it inline
  3. bench/scope_check.py: allowed writes pass, out-of-scope writes / protected files / commits fail, pre-existing
     uncommitted work is not blamed, missing snapshot or unknown role exits 2"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ROLES = {"pm": "pm-eval-loop", "ba": "ba-eval-loop", "arch": "arch-eval-loop", "dev": "dev-eval-loop",
         "doc": "doc-eval-loop", "onboard": "onboard-eval-loop", "qa": "qa-eval-loop", "devops": "devops-eval-loop",
         "sm": "sm-eval-loop"}
BASH_OK = {"dev", "qa", "devops"}
fails = 0


def ok(cond, msg):
    global fails
    fails += not cond
    print(f"{'ok ' if cond else 'FAIL'} {msg}")


for role, cmd in ROLES.items():
    agent = DIST / f"claude-code/.claude/agents/plumbline-{role}-originator.md"
    txt = agent.read_text() if agent.exists() else ""
    tools = set(re.search(r"^tools:\s*(.+)$", txt, re.M).group(1).replace(" ", "").split(",")) if txt else set()
    bad = {t for t in tools if t.startswith("mcp__") or t in ("WebFetch", "WebSearch", "Agent", "Task")}
    ok(txt and not bad and (("Bash" in tools) == (role in BASH_OK)),
       f"agent plumbline-{role}-originator least-privilege: {sorted(tools)}")
    c = (DIST / f"claude-code/.claude/commands/{cmd}.md").read_text()
    cp = (DIST / f"copilot/.github/prompts/{cmd}.prompt.md").read_text()
    ok(f"subagent_type: plumbline-{role}-originator" in c and f"--role {role}" in c and "CHECK:" in c and "@originator" not in c,
       f"/{cmd} (Claude) hands Stage 1 to the agent and runs the scope check")
    ca = DIST / f"copilot/.github/agents/plumbline-{role}-originator.agent.md"
    ctxt = ca.read_text() if ca.exists() else ""
    ctools = set(re.findall(r"'([^']+)'", re.search(r"^tools:\s*(.+)$", ctxt, re.M).group(1))) if ctxt else set()
    cbad = {t for t in ctools if t.split("/")[0] in ("web", "agent", "browser", "vscode") or "github" in t.lower()}
    ok(ctxt and "user-invocable: false" in ctxt and not cbad
       and (any(t.startswith("execute") for t in ctools) == (role in BASH_OK)),
       f"copilot agent plumbline-{role}-originator least-privilege: {sorted(ctools)}")
    ok(f"agent name `plumbline-{role}-originator`" in cp and "agent/runSubagent" in cp and "CHECK:" in cp
       and "@originator" not in cp, f"{cmd}.prompt.md (Copilot) hands Stage 1 to the subagent and runs the scope check")

crit = (DIST / "copilot/.github/agents/plumbline-critic.agent.md").read_text()
ok("tools: ['read/readFile', 'search']" in crit and "user-invocable: false" in crit, "copilot plumbline-critic agent is read-only")

SC = [sys.executable, str(ROOT / "bench/scope_check.py")]


def run(repo, *a):
    return subprocess.run(SC + list(a), cwd=repo, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as td:
    r = Path(td)
    g = lambda *a: subprocess.run(["git", *a], cwd=r, capture_output=True, check=True)
    g("init", "-q", "-b", "develop"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (r / "services/a/src").mkdir(parents=True)
    (r / "services/a/src/A.java").write_text("class A {}\n")
    (r / "services/a/pom.xml").write_text("<project><build><plugins><plugin><artifactId>maven-surefire-plugin</artifactId>"
                                          "</plugin></plugins></build></project>\n")
    (r / "CLAUDE.md").write_text("rules\n")
    (r / ".gitignore").write_text("*.log\n.plumbline/\n")
    (r / "notes.txt").write_text("user's own work\n")
    g("add", "services", "CLAUDE.md", ".gitignore"); g("commit", "-qm", "base")
    (r / "notes.txt").write_text("user's own work, still uncommitted\n")          # pre-existing dirty file
    (r / ".plumbline/review").mkdir(parents=True)
    (r / ".plumbline/review/t-input.md").write_text("the requirement\n")             # an input the originator must not edit

    def snap(writable="", role="dev"):
        out = run(r, "snapshot", "--name", "t", "--writable", writable, "--role", role).stdout
        first = out.split()
        check = next(l for l in out.splitlines() if l.startswith("CHECK: "))[len("CHECK: "):]
        return first[1], first[2], check

    def case(role, actions, expect_rc, label, writable="", guard=None):
        path, sha, check = snap(writable, role)
        for a in actions:
            a(r, path)
        # exactly what the hand-off runs: the printed CHECK line (python -I verifies the sha, then runs the copy)
        res = subprocess.run(["bash", "-c", check.replace("python3", f'"{sys.executable}"', 1)], cwd=r,
                             capture_output=True, text=True)
        last = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else res.stderr.strip()
        ok(res.returncode == expect_rc, f"scope {label} -> rc {res.returncode} {last}")
        g("checkout", "-q", "--", ".")
        subprocess.run(["git", "clean", "-qfdx", "-e", "notes.txt", "-e", ".plumbline/review/t-input.md"], cwd=r)
        (r / ".plumbline/review").mkdir(parents=True, exist_ok=True)
        (r / ".plumbline/review/t-input.md").write_text("the requirement\n")

    w = lambda p, t="x\n": (lambda rr, _s: (rr / p).parent.mkdir(parents=True, exist_ok=True) or (rr / p).write_text(t))
    case("dev", [w("services/a/src/A.java", "class A { int x; }\n"), w(".plumbline/work/t/fixlog.md")], 0, "dev edits code + fix log")
    case("dev", [w("CLAUDE.md", "relaxed\n")], 1, "dev edits the rulebook")
    case("dev", [w(".github/workflows/ci.yml")], 1, "dev adds a workflow")
    case("pm", [w("services/a/src/B.java")], 1, "pm writes code")
    case("pm", [w(".plumbline/review/t-prd.md")], 0, "pm writes its PRD", ".plumbline/review/t-prd.md")
    case("pm", [w(".plumbline/review/t-prd.md")], 1, "pm writes a .plumbline file it was not given", "")
    case("pm", [w(".plumbline/review/t-input.md", "edited\n")], 1, "pm edits its input file", ".plumbline/review/t-prd.md")
    case("pm", [w("debug.log")], 1, "pm writes a gitignored file")
    case("doc", [w("CLAUDE.md", "updated\n"), w("services/a/openapi.yaml")], 0, "doc edits CLAUDE.md + openapi")
    case("qa", [w("test-results/a.png"), w(".plumbline/review/t-qa-results.json")], 0, "qa writes evidence", ".plumbline/review/t-qa-results.json")
    case("qa", [w("services/a/src/A.java", "hack\n")], 1, "qa edits production code")
    case("dev", [w("services/a/pom.xml", "<project><properties><skipTests>true</skipTests></properties></project>\n")],
         1, "dev sets skipTests in a pom")
    case("dev", [lambda rr, sp: Path(sp, "snapshot.json").write_text("{}")], 1, "dev rewrites the snapshot")
    case("pm", [lambda rr, sp: Path(sp, "bench/scope_check.py").write_text("import sys\nsys.exit(0)\n"),
                w("services/a/src/B.java")], 1, "pm swaps the checker copy (orchestrator sha check)")
    case("pm", [lambda rr, sp: Path(sp, "gates/checks/protected_paths.py").write_text("PROTECTED = []\n")], 1,
         "pm swaps the copied protected_paths")

    case("qa", [w("frontend/test-results/qa/a.png")], 0, "qa screenshot under frontend/test-results")
    case("pm", [w("services/a/build/Gen.class")], 0, "module-root build/ output is not blamed")
    case("pm", [w("services/a/src/build/Gen.java")], 1, "pm writes a nested build/ source dir")
    def hide(rr, _s):
        subprocess.run(["git", "update-index", "--skip-worktree", "services/a/src/A.java"], cwd=rr)
        (rr / "services/a/src/A.java").write_text("hidden edit\n")
    case("pm", [hide], 1, "pm hides an edit with skip-worktree")
    subprocess.run(["git", "update-index", "--no-skip-worktree", "services/a/src/A.java"], cwd=r)
    g("checkout", "-q", "--", ".")
    case("pm", [w("odd name ü.md")], 1, "pm writes a file with spaces / non-ASCII in its name")
    def commit(rr, _s):
        (rr / "services/a/src/C.java").write_text("class C {}\n")
        subprocess.run(["git", "add", "services"], cwd=rr); subprocess.run(["git", "commit", "-qm", "sneaky"], cwd=rr)
    case("dev", [commit], 1, "dev commits")
    g("reset", "-q", "--hard", "HEAD~1")

    def side_branch(rr, _s):
        subprocess.run(["git", "branch", "side"], cwd=rr)
    case("dev", [side_branch], 1, "dev creates a branch")
    g("branch", "-D", "side")
    # a Bash-capable originator edits the .agentic-sdlc folder (a private copy here, so the real one is untouched)
    import shutil
    gcopy = Path(td + "-g")
    for d in ("bench", "gates/checks", "impact"):
        shutil.copytree(ROOT / d, gcopy / d, ignore=shutil.ignore_patterns("__pycache__"))
    out = subprocess.run([sys.executable, str(gcopy / "bench/scope_check.py"), "snapshot", "--name", "t"],
                         cwd=r, capture_output=True, text=True).stdout.split()
    with open(gcopy / "bench/run.py", "a") as fh:
        fh.write("\n# tampered\n")
    res = subprocess.run([sys.executable, "-I", out[1] + "/bench/scope_check.py", "check", "dev", "--snapshot", out[1], "--sha", out[2]],
                         cwd=r, capture_output=True, text=True)
    ok(res.returncode == 1 and "<agentic-sdlc>" in res.stdout, "dev edits the .agentic-sdlc folder -> rc %d" % res.returncode)
    shutil.rmtree(gcopy)
    res = run(r, "check", "nope", "--snapshot", "x", "--sha", "y")
    ok(res.returncode == 2, "unknown role exits 2")
    res = run(r, "check", "dev", "--snapshot", str(r / "missing.json"), "--sha", "0")
    ok(res.returncode == 2, "missing snapshot exits 2")

total = len(ROLES) * 4 + 26
print(f"agents selftest: {total - fails}/{total}")
sys.exit(1 if fails else 0)
