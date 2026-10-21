#!/usr/bin/env python3
"""Self-test for repository layouts (impact/layout.py): a single Spring app at the repo root + a frontend in ui/,
and the same repo declared through .plumbline/project.yaml. Checks that units, the dependency map (working tree
and git ref), the benchmark, the scope check and the gates all see the root app."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impact"))
import layout  # noqa: E402
fails = 0


def ok(cond, msg):
    global fails
    fails += not cond
    print(f"{'ok ' if cond else 'FAIL'} {msg}")


def w(r, p, t):
    (r / p).parent.mkdir(parents=True, exist_ok=True)
    (r / p).write_text(t)


with tempfile.TemporaryDirectory() as td:
    r = Path(td) / "shop"
    r.mkdir()
    g = lambda *a: subprocess.run(["git", *a], cwd=r, capture_output=True, text=True, check=True).stdout
    g("init", "-q", "-b", "develop"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    w(r, "pom.xml", "<project><groupId>x</groupId><artifactId>shop</artifactId><version>1</version></project>\n")
    w(r, "src/main/resources/application.yml", "server:\n  port: 8081\nspring:\n  application:\n    name: shop\n")
    w(r, "src/main/java/com/x/controller/OrderController.java",
      'package com.x.controller;\n@RestController\n@RequestMapping("/api/orders")\npublic class OrderController {\n'
      '  @GetMapping("/{id}")\n  public Object get(@PathVariable String id) { return null; }\n}\n')
    w(r, "ui/package.json", '{"name":"ui"}\n')
    w(r, "ui/src/api.ts", "export const get = (id: string) => fetch(`/api/orders/${id}`);\n")
    w(r, "CLAUDE.md", "# shop\n")
    w(r, "docs/notes.md", "notes\n")
    g("add", "-A"); g("commit", "-qm", "base")

    u = layout.units(r)
    ok([(x["name"], x["path"], x["kind"]) for x in u] == [("shop", ".", "service"), ("ui", "ui", "frontend")],
       f"layout: root app + ui frontend -> {[(x['name'], x['path'], x['kind']) for x in u]}")
    ok(layout.unit_of("src/main/java/A.java", u)["name"] == "shop" and layout.unit_of("ui/src/x.ts", u)["name"] == "ui"
       and layout.unit_of("docs/notes.md", u) is None, "unit_of: src/ -> root app, ui/ -> ui, docs/ -> none")

    import depmap
    for ref in (None, "HEAD"):
        dm = depmap.build(r, None, ref)
        s = dm["services"].get("shop") or {}
        ok(s.get("path") == "." and s.get("port") == 8081 and any(p["path"] == "/api/orders/{*}" for p in s.get("provides", [])),
           f"depmap ({ref or 'working tree'}): root app found with port and endpoint -> {s.get('path')}, {s.get('port')}")
        ok("ui" in dm["services"] and dm["services"]["ui"]["kind"] == "frontend", f"depmap ({ref or 'working tree'}): ui is a frontend")

    # benchmark: onboard pack on the root app
    w(r, ".plumbline/run/review/shop-CLAUDE.md", "# CLAUDE.md — shop\n## 1. Service Purpose\nOrders.\n## 2. Port\n8081\n"
      "## 3. Database Schema\nnone\n## 4. Kafka Topics Produced\nnone\n## 5. Kafka Topics Consumed\nnone\n"
      "## 6. Redis Cache Keys Owned\nnone\n## 7. REST Endpoints Exposed\n- GET /api/orders/{id}\n"
      "## 8. REST Endpoints Called\nnone\n## 9. Entities Owned\nnone\n## 10. What This Service Must NEVER Do\n- x\n"
      "## 11. Key Business Rules\n- y\n")
    b = subprocess.run([sys.executable, str(ROOT / "bench/run.py"), "onboard", "--artifact", ".plumbline/run/review/shop-CLAUDE.md",
                        "--repo", ".", "--service", "shop", "--name", "shop-onboard"], cwd=r, capture_output=True, text=True)
    rep = json.loads((r / ".plumbline/run/review/shop-onboard-benchmark.json").read_text()) if b.returncode in (0, 1) else {}
    chk = {c["id"]: c["result"] for c in rep.get("checks", [])}
    ok(b.returncode in (0, 1) and chk.get("OB-2") == "PASS" and chk.get("OB-4") == "PASS" and chk.get("OB-5") == "PASS",
       f"bench onboard on the root app: rc {b.returncode}, port/endpoints {chk.get('OB-2')}/{chk.get('OB-4')}/{chk.get('OB-5')}"
       + ("" if b.returncode in (0, 1) else f" — {b.stderr.strip()[-200:]}"))

    # dev pack sees the root app as the changed unit
    sys.path.insert(0, str(ROOT / "bench")); sys.path.insert(0, str(ROOT / "bench/packs"))
    import dev
    w(r, "src/main/java/com/x/service/OrderService.java", "package com.x.service;\npublic class OrderService {}\n")
    svcs, _ = dev.changed_services(r, "develop")
    ok(svcs == ["shop"] and dev.UNITS == {"shop": ""}, f"dev pack: changed unit -> {svcs} {dev.UNITS}")

    # scope check: dev may change src/ and ui/, not docs/ or the root rulebook
    SC = [sys.executable, str(ROOT / "bench/scope_check.py")]
    def scope(role, path, text="x\n"):
        out = subprocess.run(SC + ["snapshot", "--name", "t"], cwd=r, capture_output=True, text=True).stdout.split()
        w(r, path, text)
        res = subprocess.run([sys.executable, "-I", out[1] + "/bench/scope_check.py", "check", role, "--snapshot", out[1],
                              "--sha", out[2]], cwd=r, capture_output=True, text=True)
        g("checkout", "-q", "--", "."); subprocess.run(["git", "clean", "-qfd", "-e", ".plumbline"], cwd=r)
        return res.returncode
    ok(scope("dev", "src/main/java/com/x/B.java") == 0, "scope: dev writes src/ of the root app")
    ok(scope("dev", "ui/src/b.ts") == 0, "scope: dev writes ui/")
    ok(scope("dev", "docs/notes.md", "changed\n") == 1, "scope: dev may not write docs/")
    ok(scope("dev", "CLAUDE.md", "relaxed\n") == 1, "scope: dev may not edit the rulebook")
    ok(scope("pm", "src/main/java/com/x/B.java") == 1, "scope: pm may not write code")
    ok(scope("doc", "CLAUDE.md", "updated\n") == 0, "scope: doc updates the master CLAUDE.md")
    ok(scope("doc", "src/CLAUDE.md", "unit doc\n") == 0, "scope: doc writes the root app's own CLAUDE.md (src/CLAUDE.md)")
    ok(scope("dev", "src/CLAUDE.md", "relaxed\n") == 1, "scope: dev may not write src/CLAUDE.md")
    ok(layout.claude_md(u[0]) == "src/CLAUDE.md" and layout.claude_md(u[1]) == "ui/CLAUDE.md",
       "claude_md: root app -> src/CLAUDE.md, ui -> ui/CLAUDE.md")

    # claude_merge: keeps human content, replaces only its block, refuses broken markers
    CM = [sys.executable, str(ROOT / "bench/claude_merge.py")]
    w(r, ".plumbline/run/review/d1.md", "# CLAUDE.md — shop\n## 1. Service Purpose\nv1\n")
    w(r, ".plumbline/run/review/d2.md", "# CLAUDE.md — shop\n## 1. Service Purpose\nv2\n")
    human = "# Runbook\nrun: ./mvnw spring-boot:run\n"
    w(r, "CLAUDE.md", human)
    subprocess.run(CM + ["--target", "CLAUDE.md", "--block", "solution", "--from", ".plumbline/run/review/d1.md", "--write"], cwd=r,
                   capture_output=True)
    subprocess.run(CM + ["--target", "CLAUDE.md", "--block", "solution", "--from", ".plumbline/run/review/d2.md", "--write"], cwd=r,
                   capture_output=True)
    m = (r / "CLAUDE.md").read_text()
    ok(m.startswith(human) and "v2" in m and "v1" not in m and m.count("plumbline:begin solution") == 1,
       "claude_merge: human runbook kept, block replaced (not duplicated)")
    dry = subprocess.run(CM + ["--target", "src/CLAUDE.md", "--block", "onboard", "--from", ".plumbline/run/review/d1.md"], cwd=r,
                         capture_output=True, text=True)
    ok(dry.returncode == 0 and not (r / "src/CLAUDE.md").exists() and "+## 1. Service Purpose" in dry.stdout,
       "claude_merge: without --write it only prints the diff")
    w(r, "CLAUDE.md", human + "<!-- plumbline:begin solution -->\nbroken\n")
    bad = subprocess.run(CM + ["--target", "CLAUDE.md", "--block", "solution", "--from", ".plumbline/run/review/d1.md", "--write"],
                         cwd=r, capture_output=True, text=True)
    ok(bad.returncode == 2 and "broken" in (r / "CLAUDE.md").read_text(), "claude_merge: unbalanced markers refused, file untouched")
    g("checkout", "-q", "--", "."); subprocess.run(["git", "clean", "-qfd", "-e", ".plumbline"], cwd=r)
    ok(scope("dev", "build.gradle", "test { enabled = false }\n") == 1, "scope: dev may not change a Gradle build file")
    ok(scope("dev", "gradle/wrapper/gradle-wrapper.properties", "distributionUrl=x\n") == 1, "scope: dev may not change the wrapper")
    ok(scope("dev", "pom.xml", "<project><build><sourceDirectory>hidden</sourceDirectory></build></project>\n") == 1,
       "scope: dev may not move the source directory in pom.xml")

    # gates: findings in the root app are reported at their real path
    if shutil.which("semgrep"):
        w(r, "src/main/java/com/x/domain/Money.java", "package com.x.domain;\npublic class Money { private double amount; }\n")
        out = subprocess.run([sys.executable, str(ROOT / "gates/run_gates.py"), ".", "--json"], cwd=r, capture_output=True, text=True)
        try:
            new = json.loads(out.stdout)["new"]
        except ValueError:
            new = []
        paths = sorted({f["path"] for f in new})
        ok(any(p == "src/main/java/com/x/domain/Money.java" for p in paths) and not any(p.startswith("services/") for p in paths),
           f"gates scan the root app and report real paths -> {paths[:3]} {out.stderr.strip()[-150:]}")
        g("clean", "-qfd", "-e", ".plumbline")
    else:
        print("skip gates (semgrep not installed)")

    # project.yaml cannot point the gates outside their scan copy
    import importlib
    for bad in ('[{name: "../../x", path: ., kind: service}]', '[{name: a, path: ../up, kind: service}]',
                '[{name: a, path: ., kind: service}, {name: a, path: ui, kind: frontend}]'):
        w(r, ".plumbline/project.yaml", "units: " + bad + "\n")
        try:
            layout.units(r); refused = False
        except SystemExit:
            refused = True
        ok(refused, f"project.yaml refused: {bad}")
    # explicit layout wins
    w(r, ".plumbline/project.yaml", "units:\n  - {name: backend, path: ., kind: service}\n  - {name: web, path: ui, kind: frontend}\n")
    u2 = layout.units(r)
    ok([(x["name"], x["path"]) for x in u2] == [("backend", "."), ("web", "ui")], f"project.yaml overrides detection -> {u2}")

total = 27 + (1 if shutil.which("semgrep") else 0)
print(f"layout selftest: {total - fails}/{total}")
sys.exit(1 if fails else 0)
