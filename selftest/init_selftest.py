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
    shutil.copytree(kit / ".agentic-sdlc", r / ".agentic-sdlc")
    init = [sys.executable, str(r / ".agentic-sdlc/init.py")]

    res = subprocess.run(init, cwd=r, capture_output=True, text=True)
    out = res.stdout
    proj = (r / ".agentic-sdlc/project.yaml").read_text() if (r / ".agentic-sdlc/project.yaml").exists() else ""
    ok("{name: det, path: ., kind: service}" in proj and "{name: ui, path: ui, kind: frontend}" in proj,
       "init: project.yaml declares the root app and ui")
    ok("domain_pack: none" in proj and "java-generic.yml" in proj and "base_branch: develop" in proj,
       "init: no domain pack, generic gates only, base branch detected")
    ok((r / ".claude/commands/onboard-eval-loop.md").is_file() and (r / ".github/agents/plumbline-critic.agent.md").is_file()
       and (r / ".github/workflows/plumbline-critic.yml").is_file() and ".plumbline/" in (r / ".gitignore").read_text(),
       "init: generated agent files, workflows and .gitignore installed")
    ok("Java 17" in out and "port 8080" in out, "doctor: Java 17 from pom.xml, default port 8080 (no server.port)")
    ok("endpoints 2 " in out, "doctor: commented-out mappings are not endpoints (2 real ones)")
    ok("angular 18.1.0" in out and "unresolved 0" in out, "doctor: Angular detected; constant/class-field URLs all resolved")
    ok("/api/opt/create" in out and "frontend call(s) have no matching endpoint" in out, "doctor: the call to a missing endpoint is reported")
    ok("CRLF" in out, "doctor: CRLF mvnw flagged")
    ok("src/CLAUDE.md" in out and (r / "CLAUDE.md").read_text() == "# Runbook\nRun: ./mvnw spring-boot:run\n",
       "root app's CLAUDE.md location is src/CLAUDE.md; the root runbook is untouched")
    if shutil.which("semgrep"):
        ok((r / ".agentic-sdlc/gates/baseline.json").is_file() and "order-service" not in
           (r / ".agentic-sdlc/gates/baseline.json").read_text(), "init: this repository's own gate baseline written")
    proj_before = proj
    res2 = subprocess.run(init, cwd=r, capture_output=True, text=True)
    ok((r / ".agentic-sdlc/project.yaml").read_text() == proj_before and "not changed" in res2.stdout,
       "init again: project.yaml kept")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 0, f"--check passes on a fresh install: {chk.stdout.strip().splitlines()[-1:]}")
    (r / ".claude/commands/dev-eval-loop.md").write_text("hand edited\n")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "stale" in chk.stdout, "--check fails when a generated file was hand-edited")
    w(r, "billing/pom.xml", "<project><artifactId>billing</artifactId></project>\n")
    w(r, "billing/src/main/java/B.java", "class B {}\n")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "billing" in chk.stdout, "--check fails when a new unit is not declared in project.yaml")
    shutil.rmtree(r / "billing")
    (r / ".github/workflows/legacy-critic.yml").write_text("old\n")
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "left over" in chk.stdout, "--check flags files left over from an older install")
    (r / ".github/workflows/legacy-critic.yml").unlink()
    pj = (r / ".agentic-sdlc/project.yaml").read_text()
    (r / ".agentic-sdlc/project.yaml").unlink()
    chk = subprocess.run(init + ["--check"], cwd=r, capture_output=True, text=True)
    ok(chk.returncode == 1 and "project.yaml missing" in chk.stdout, "--check fails without project.yaml")
    (r / ".agentic-sdlc/project.yaml").write_text(pj)
    # upgrade keeps project.yaml and the baseline, refreshes the rest; a project.yaml inside the tarball is ignored
    (kit / ".agentic-sdlc/project.yaml").write_text("units: []\ndomain_pack: evil\n")
    tgz = Path(td) / "kit.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        tf.add(kit / ".agentic-sdlc", arcname=".agentic-sdlc")
    (r / ".agentic-sdlc/README.md").write_text("old\n")
    up = subprocess.run(init + ["--upgrade", str(tgz)], cwd=r, capture_output=True, text=True)
    ok(up.returncode in (0, 1) and (r / ".agentic-sdlc/project.yaml").read_text() == proj_before
       and (r / ".agentic-sdlc/README.md").read_text() != "old\n"
       and (r / ".claude/commands/dev-eval-loop.md").read_text() != "hand edited\n",
       f"--upgrade: framework replaced, project.yaml kept, generated files refreshed ({up.stdout.strip().splitlines()[:1]})")

total = 16 + (1 if shutil.which("semgrep") else 0)
print(f"init selftest: {total - fails}/{total}")
sys.exit(1 if fails else 0)
