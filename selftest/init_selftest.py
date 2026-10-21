#!/usr/bin/env python3
"""Self-test for init.py on a fixture shaped like candidate-review-system (a Spring Boot app at the repository root,
Java 17, application.properties without server.port, an Angular ui/ that builds URLs from constants and class fields,
a commented-out mapping, a call to an endpoint that does not exist, MSAL cache in localStorage, a CRLF mvnw, and a
human runbook in the root CLAUDE.md). Locks in the fixes found on that repository."""
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fails = 0


def ok(cond, msg):
    global fails
    fails += not cond
    print(f"{'ok ' if cond else 'FAIL'} {msg}")


def w(r, p, t, crlf=False):
    (r / p).parent.mkdir(parents=True, exist_ok=True)
    (r / p).write_bytes(t.replace("\n", "\r\n").encode() if crlf else t.encode())


def fixture(r: Path):
    w(r, "pom.xml", "<project><artifactId>det</artifactId><properties><java.version>17</java.version></properties></project>\n")
    w(r, "mvnw", "#!/bin/sh\necho mvn\n", crlf=True)
    w(r, "CLAUDE.md", "# Runbook\nRun: ./mvnw spring-boot:run\n")
    w(r, "src/main/resources/application.properties", "server.servlet.context-path=/\nspring.datasource.url=jdbc:sqlite:det.db\n")
    w(r, "src/main/java/com/x/DetApplication.java", "package com.x;\n@SpringBootApplication\npublic class DetApplication {}\n")
    w(r, "src/main/java/com/x/controller/OptController.java",
      'package com.x.controller;\n@RestController\n@RequestMapping("/api/opt")\npublic class OptController {\n'
      '  @GetMapping("/opportunities/{id}")\n  public Object get(@PathVariable String id) { return null; }\n'
      '  // @PostMapping("/legacy")\n  // public Object legacy() { return null; }\n'
      '  /* @GetMapping("/old") */\n}\n')
    w(r, "src/main/java/com/x/controller/AdminController.java",
      'package com.x.controller;\n@RestController\n@RequestMapping("/api/opt/reference")\npublic class AdminController {\n'
      '  @GetMapping("/admin/{table}")\n  public Object list(@PathVariable String table) { return null; }\n}\n')
    w(r, "ui/package.json", '{"name":"ui","dependencies":{"@angular/core":"^18.1.0"}}\n')
    w(r, "ui/src/app/constants.ts",
      "export const API_BASE_URL = environment.BASE_API_URL;\n"
      "export const OPT_ENDPOINTS = {\n  OPPORTUNITIES: '/api/opt/opportunities',\n  CREATE: '/api/opt/create',\n};\n"
      "export const REF = {\n  ADMIN: '/api/opt/reference/admin',\n};\n")
    w(r, "ui/src/app/services/opt.service.ts",
      "export class OptService {\n  get(id: string) { return this.http.get<Record<string, number>>(`${API_BASE_URL}${OPT_ENDPOINTS.OPPORTUNITIES}/${id}`); }\n"
      "  create(p: any) { return this.http.post(`${API_BASE_URL}${OPT_ENDPOINTS.CREATE}`, p); }\n}\n")
    w(r, "ui/src/app/components/admin.component.ts",
      "export class AdminComponent {\n  private readonly baseUrl = `${API_BASE_URL}${REF.ADMIN}`;\n"
      "  load(t: string) { return this.http.get<any[]>(`${this.baseUrl}/${t}`); }\n}\n")
    w(r, "ui/src/app/other.component.ts",
      "export class Other {\n  private readonly baseUrl = '/somewhere/else';\n  x() { return this.http.get(`${this.baseUrl}/y`); }\n}\n")
    w(r, "ui/src/app/msal.config.ts", "export const c = { cache: { cacheLocation: BrowserCacheLocation.LocalStorage } };\n")


with tempfile.TemporaryDirectory() as td:
    kit = Path(td) / "kit"
    subprocess.run([sys.executable, str(ROOT / "tools/make_kit.py"), "--out", str(kit)], check=True, capture_output=True)
    r = Path(td) / "det"
    r.mkdir()
    g = lambda *a: subprocess.run(["git", *a], cwd=r, capture_output=True, text=True)
    g("init", "-q", "-b", "develop"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    fixture(r)
    g("add", "-A"); g("commit", "-qm", "base")
    shutil.copytree(kit / ".plumbline", r / ".plumbline")
    init = [sys.executable, str(r / ".plumbline/init.py")]

    res = subprocess.run(init, cwd=r, capture_output=True, text=True)
    out = res.stdout
    proj = (r / ".plumbline/project.yaml").read_text() if (r / ".plumbline/project.yaml").exists() else ""
    ok("{name: det, path: ., kind: service}" in proj and "{name: ui, path: ui, kind: frontend}" in proj,
       "init: project.yaml declares the root app and ui")
    ok("domain_pack: none" in proj and "java-generic.yml" in proj and "base_branch: develop" in proj,
       "init: no domain pack, generic gates only, base branch detected")
    ok((r / ".claude/commands/plumbline-onboard.md").is_file() and (r / ".github/agents/plumbline-critic.agent.md").is_file()
       and not (r / ".github/workflows").exists() and not (r / ".gitignore").exists()
       and "run/" in (r / ".plumbline/.gitignore").read_text(),
       "init: plumbline-* entry files installed; no CI workflows unless --ci; root .gitignore untouched")
    st = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=r, capture_output=True, text=True).stdout.split("\n")
    outside = [l[3:] for l in st if l.strip() and not l[3:].startswith(".plumbline/")
               and not __import__("re").match(r"(\.claude/(commands|agents)|\.github/(prompts|agents))/plumbline-", l[3:])]
    ok(not outside, f"footprint: nothing outside .plumbline/ except plumbline-* entry files {outside[:5]}")
    ok("Java 17" in out and "port 8080" in out, "doctor: Java 17 from pom.xml, default port 8080 (no server.port)")
    ok("endpoints 2 " in out, "doctor: commented-out mappings are not endpoints (2 real ones)")
    ok("angular 18.1.0" in out and "unresolved 0" in out, "doctor: Angular detected; constant/class-field URLs all resolved")
    ok("/api/opt/create" in out and "frontend call(s) have no matching endpoint" in out, "doctor: the call to a missing endpoint is reported")
    ok("CRLF" in out, "doctor: CRLF mvnw flagged")
    ok("src/CLAUDE.md" in out and (r / "CLAUDE.md").read_text() == "# Runbook\nRun: ./mvnw spring-boot:run\n",
       "root app's CLAUDE.md location is src/CLAUDE.md; the root runbook is untouched")
    if shutil.which("semgrep"):
        ok((r / ".plumbline/gates/baseline.json").is_file() and "order-service" not in
           (r / ".plumbline/gates/baseline.json").read_text(), "init: this repository's own gate baseline written")
    import re as _re
    left = [str(f.relative_to(r)) for d in (".claude", ".github") for f in (r / d).rglob("*.md")
            if _re.search(r"\{\{(JIRA_KEY|CONFLUENCE_SPACE|API_URL|FRONTEND_URL|LOGIN_PATH)\}\}", f.read_text())]
    qa = (r / ".claude/commands/plumbline-qa.md").read_text()
    ok(not left and "PROJ-{n}" in qa and "http://localhost:4200" in qa and "SCRUM" not in qa
       and "JIRA project key not set" in out and not (kit / ".plumbline/gates/baseline.json").exists(),
       f"generic: settings rendered (PROJ, Angular port 4200), no SCRUM, key-not-set flagged, no baseline shipped {left[:3]}")
    proj_before = proj
    res2 = subprocess.run(init, cwd=r, capture_output=True, text=True)
    ok((r / ".plumbline/project.yaml").read_text() == proj_before and "not changed" in res2.stdout,
       "init again: project.yaml kept")
    subprocess.run(init + ["--jira", "CRS"], cwd=r, capture_output=True, text=True)
    pj = (r / ".plumbline/project.yaml").read_text()
    ok("jira_project: CRS" in pj and "confluence_space: CRS" in pj and "CRS-{n}" in (r / ".github/prompts/plumbline-dev.prompt.md").read_text(),
       "--jira CRS: project.yaml updated (Confluence follows) and entry files re-rendered")
    proj_before = (r / ".plumbline/project.yaml").read_text()
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    if shutil.which("semgrep"):
        ok(chk.returncode == 0, f"--check passes on a fresh install: {chk.stdout.strip().splitlines()[-1:]}")
    else:   # without Semgrep no baseline can be written: that must be the only complaint
        fails_ = [l for l in chk.stdout.splitlines() if l.startswith("FAIL") and "plumbline check" not in l]
        ok(len(fails_) == 1 and "baseline" in fails_[0], f"--check without Semgrep fails only on the baseline: {fails_}")
    (r / ".claude/commands/plumbline-dev.md").write_text("hand edited\n")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "stale" in chk.stdout, "--check fails when a generated file was hand-edited")
    w(r, "billing/pom.xml", "<project><artifactId>billing</artifactId></project>\n")
    w(r, "billing/src/main/java/B.java", "class B {}\n")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "billing" in chk.stdout, "--check fails when a new unit is not declared in project.yaml")
    shutil.rmtree(r / "billing")
    (r / ".github/workflows").mkdir(parents=True, exist_ok=True)
    (r / ".github/workflows/legacy-critic.yml").write_text("run: python3 .agentic-sdlc/gates/run_gates.py\n")
    (r / ".github/workflows/team-lint.yml").write_text("run: npm run lint\n")   # the team's own: never flagged
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "legacy-critic.yml" in chk.stdout and "team-lint" not in chk.stdout,
       "--check flags files left over from an older install, never the team's own")
    (r / ".github/workflows/team-lint.yml").unlink()
    (r / ".github/workflows/legacy-critic.yml").unlink()
    pj = (r / ".plumbline/project.yaml").read_text()
    (r / ".plumbline/project.yaml").unlink()
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "project.yaml missing" in chk.stdout, "--check fails without project.yaml")
    (r / ".plumbline/project.yaml").write_text(pj)
    ci = subprocess.run(init + ["--ci", "--no-baseline"], cwd=r, capture_output=True, text=True)
    ok((r / ".github/workflows/plumbline-guardrails.yml").is_file() and (r / ".github/workflows/plumbline-critic.yml").is_file(),
       "--ci installs the plumbline-* workflows")
    # upgrade keeps project.yaml and the baseline, refreshes the rest; a project.yaml inside the tarball is ignored
    (kit / ".plumbline/project.yaml").write_text("units: []\ndomain_pack: evil\n")
    tgz = Path(td) / "kit.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        tf.add(kit / ".plumbline", arcname=".plumbline")
    (r / ".plumbline/README.md").write_text("old\n")
    up = subprocess.run(init + ["--upgrade", str(tgz)], cwd=r, capture_output=True, text=True)
    ok(up.returncode in (0, 1) and (r / ".plumbline/project.yaml").read_text() == proj_before
       and (r / ".plumbline/README.md").read_text() != "old\n"
       and (r / ".claude/commands/plumbline-dev.md").read_text() != "hand edited\n",
       f"--upgrade: framework replaced, project.yaml kept, generated files refreshed ({up.stdout.strip().splitlines()[:1]})")

    # uninstall: dry run lists, --yes removes; CLAUDE.md files stay
    w(r, "src/CLAUDE.md", "unit doc\n")
    dry = subprocess.run(init + ["--uninstall"], cwd=r, capture_output=True, text=True)
    ok((r / ".plumbline").is_dir() and "Nothing removed" in dry.stdout, "--uninstall without --yes removes nothing")
    gone = subprocess.run(init + ["--uninstall", "--yes"], cwd=r, capture_output=True, text=True)
    left = [str(p.relative_to(r)) for p in r.rglob("*") if ".git" not in p.parts and p.is_file()
            and ("plumbline" in p.name or ".plumbline" in p.parts)]
    ok(gone.returncode == 0 and not (r / ".plumbline").exists() and not left and (r / "src/CLAUDE.md").is_file(),
       f"--uninstall --yes removes every Plumbline file, keeps CLAUDE.md {left[:3]}")

    # migration from the 1.9 layout (.agentic-sdlc/ framework, .plumbline/ working files, root .gitignore line)
    m = Path(td) / "old"
    m.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=m)
    fixture(m)
    w(m, ".agentic-sdlc/project.yaml", "units:\n  - {name: det, path: ., kind: service}\ndomain_pack: none\n")
    w(m, ".agentic-sdlc/gates/baseline.json", '{"fingerprints": {}}\n')
    w(m, ".agentic-sdlc/VERSION", "v1.9.0\n")
    w(m, ".plumbline/review/det-CLAUDE.md", "draft\n")
    w(m, ".gitignore", "target/\n.plumbline/\n")
    with tarfile.open(tgz) as tf:
        tf.extract(".plumbline/init.py", m, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    up = subprocess.run([sys.executable, str(m / ".plumbline/init.py"), "--upgrade", str(tgz)], cwd=m, capture_output=True, text=True)
    ok(not (m / ".agentic-sdlc").exists() and (m / ".plumbline/project.yaml").read_text().startswith("units:")
       and "det" in (m / ".plumbline/project.yaml").read_text()
       and (m / ".plumbline/gates/baseline.json").read_text() == '{"fingerprints": {}}\n'
       and (m / ".plumbline/run/review/det-CLAUDE.md").read_text() == "draft\n"
       and (m / ".gitignore").read_text() == "target/\n" and (m / ".plumbline/loops").is_dir(),
       f"migration from 1.9: config, baseline and drafts kept, .agentic-sdlc removed, root .gitignore line removed "
       f"{up.stdout.strip().splitlines()[:6]} {up.stderr.strip()[-200:]}")

total = 24 + (1 if shutil.which("semgrep") else 0)
print(f"init selftest: {total - fails}/{total}")
sys.exit(1 if fails else 0)
