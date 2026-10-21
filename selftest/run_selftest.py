#!/usr/bin/env python3
"""Self-test for the gates: every `// expect: RULE[, RULE]` marker in selftest/fixture must be reported on that line,
CleanService.java must produce no findings, and the migration fixtures must trip the Flyway rules.
Run: python3 selftest/run_selftest.py   (exit 1 on any mismatch)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "selftest" / "fixture"

out = subprocess.run([sys.executable, str(ROOT / "gates" / "run_gates.py"), str(FIX), "--json", "--all-packs"],
                     capture_output=True, text=True)
new = json.loads(out.stdout)["new"]
got = {(f["path"], f["line"], f["rule"]) for f in new}

expected = set()
for f in FIX.rglob("*.java"):
    rel = str(f.relative_to(FIX))
    for i, line in enumerate(f.read_text().splitlines(), 1):
        m = re.search(r"// expect: (.+)$", line)
        if m:
            for rule in (r.strip() for r in m.group(1).split(",")):
                expected.add((rel, i, rule))
mig = "services/order-service/src/main/resources/db/migration/"
expected.add((mig + "V1__drop_tmp.sql", 1, "C12-flyway-destructive"))
expected.add((mig + "v2-bad-name.sql", 1, "C12-flyway-filename"))
expected.add(("tools/src/main/java/x/Helper.java", 1, "C5-java-outside-services"))

missing = sorted(expected - got)
clean_hits = sorted(x for x in got if "CleanService" in x[0])
fails = 0
for x in missing:
    print("MISSING ", x); fails += 1
for x in clean_hits:
    print("FALSE+  ", x); fails += 1
extra = sorted(x for x in got - expected if "CleanService" not in x[0])
for x in extra:
    print("extra   ", x)          # informational: findings without an expect marker
print(f"selftest: {len(expected) - len(missing)}/{len(expected)} expected findings, {len(clean_hits)} false positives on clean code")

# ── Baseline: debt passes, a duplicate of a baselined line is NEW ──
import shutil
import tempfile
with tempfile.TemporaryDirectory() as td:
    work = Path(td) / "repo"
    shutil.copytree(FIX, work)
    base = Path(td) / "baseline.json"
    gates = [sys.executable, str(ROOT / "gates" / "run_gates.py"), str(work), "--all-packs"]
    subprocess.run(gates + ["--write-baseline", str(base)], capture_output=True, check=True)
    ok_clean = subprocess.run(gates + ["--baseline", str(base)], capture_output=True).returncode == 0
    svc = work / "services/order-service/src/main/java/com/brokerdealer/orderservice/service/BadService.java"
    t = svc.read_text()
    svc.write_text(t.replace("        o.setStatus(OrderStatus.EXPIRED);", "        o.setStatus(OrderStatus.EXPIRED);\n        o.setStatus(OrderStatus.EXPIRED);", 1))
    r = subprocess.run(gates + ["--baseline", str(base), "--json"], capture_output=True, text=True)
    dup_new = json.loads(r.stdout)["new"]
    ok_dup = len(dup_new) == 1 and dup_new[0]["rule"] == "DOM-SM-direct-setstatus"
    print(f"baseline: debt passes={ok_clean}, duplicate of baselined line is NEW={ok_dup}")
    fails += (not ok_clean) + (not ok_dup)

# ── protected_paths.py scenarios on a scratch git repo ──
PP = ROOT / "gates" / "checks" / "protected_paths.py"
POM = ("<project><dependencies><dependency><artifactId>lib</artifactId><version>1</version></dependency></dependencies>"
       "<build><plugins><plugin><artifactId>jacoco-maven-plugin</artifactId><configuration><rules><minimum>0.80</minimum>"
       "</rules></configuration></plugin><plugin><artifactId>maven-surefire-plugin</artifactId></plugin></plugins></build></project>")
scenarios = [  # (branch, change(fn), env policy, expect_violation)
    ("feature/deps", lambda r: (r / "pom.xml").write_text(POM.replace("<version>1</version>", "<version>2</version>")), False, False),
    ("ai/cov", lambda r: (r / "pom.xml").write_text(POM.replace("<minimum>0.80</minimum>", "<minimum>0.10</minimum>")), False, True),
    ("ai/surefire", lambda r: (r / "pom.xml").write_text(POM.replace("<artifactId>maven-surefire-plugin</artifactId>", "<artifactId>maven-surefire-plugin</artifactId><configuration><testFailureIgnore>true</testFailureIgnore></configuration>")), False, True),
    ("docs/rules", lambda r: (r / "CLAUDE.md").write_text("changed"), False, True),
    ("feature/ignore", lambda r: (r / "services").mkdir() or (r / "services/.semgrepignore").write_text("*"), False, True),
    ("feature/rename", lambda r: subprocess.run(["git", "mv", "CLAUDE.md", "RULES.md"], cwd=r, check=True), False, True),
    ("feature/ci", lambda r: (r / ".github/workflows/ci.yml").write_text("changed"), False, True),
    ("ai/split-tag", lambda r: (r / "pom.xml").write_text(POM.replace("<artifactId>maven-surefire-plugin</artifactId></plugin>", "<artifactId>\n  maven-surefire-plugin\n</artifactId><configuration><skip>true</skip></configuration></plugin>")), False, True),
    ("ai/mvn-config", lambda r: (r / ".mvn").mkdir() or (r / ".mvn/maven.config").write_text("-DskipTests"), False, True),
    ("ai/claude-local", lambda r: (r / "CLAUDE.local.md").write_text("relax"), False, True),
    ("ai/copilot-rules", lambda r: (r / ".github/copilot-instructions.md").write_text("relax"), False, True),
    ("ai/gitattributes", lambda r: (r / ".gitattributes").write_text("*.java working-tree-encoding=UTF-16LE"), False, True),
    ("policy/ci", lambda r: (r / ".github/workflows/ci.yml").write_text("changed"), True, False),
]
import os
for branch, change, policy, expect in scenarios:
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        run = lambda *a: subprocess.run(["git", *a], cwd=r, capture_output=True, check=True)
        run("init", "-q", "-b", "develop"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        (r / "pom.xml").write_text(POM); (r / "CLAUDE.md").write_text("rules")
        (r / ".github/workflows").mkdir(parents=True); (r / ".github/workflows/ci.yml").write_text("ci")
        run("add", "-A"); run("commit", "-qm", "base"); run("checkout", "-qb", branch)
        change(r); run("add", "-A"); run("commit", "-qm", "change")
        env = {**os.environ, "PLUMBLINE_POLICY_PR": "1" if policy else "0"}
        got_violation = subprocess.run([sys.executable, str(PP), "develop", "HEAD"], cwd=r, env=env,
                                       capture_output=True).returncode == 1
        status = "ok" if got_violation == expect else "FAIL"
        print(f"protected-paths {branch:16} expect_violation={expect!s:5} -> {status}")
        fails += status == "FAIL"

# ── a source file that is not UTF-8 (e.g. re-encoded on checkout) fails the gate instead of passing unscanned ──
with tempfile.TemporaryDirectory() as td:
    work = Path(td) / "repo"
    shutil.copytree(FIX, work)
    f = work / "services/order-service/src/main/java/com/brokerdealer/orderservice/service/BadService.java"
    f.write_bytes(f.read_text().encode("utf-16-le"))
    r = subprocess.run([sys.executable, str(ROOT / "gates" / "run_gates.py"), str(work), "--all-packs"], capture_output=True, text=True)
    ok = r.returncode != 0 and "not plain UTF-8" in (r.stdout + r.stderr)
    print(f"non-UTF-8 source fails closed: {ok}")
    fails += not ok

sys.exit(1 if fails else 0)
