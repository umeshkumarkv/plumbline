#!/usr/bin/env python3
"""Self-test for bench/: every agent's benchmark must PASS its good fixture and FAIL its bad fixture on exactly the
planted checks. Fixtures: selftest/bench-fixture/{repo,good,bad}. Dev/code-review/doc run on scratch git repos."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "selftest/bench-fixture"
REPO = FX / "repo"
RUN = [sys.executable, str(ROOT / "bench/run.py")]

CASES = [  # (agent, args builder(variant), FAIL ids the bad variant must produce — and nothing else may FAIL)
    ("pm", lambda v: ["--artifact", f"{FX}/{v}/prd.md", "--repo", str(REPO)], {"PM-2", "PM-5", "PM-6", "PM-7", "PM-8", "PM-9"}),
    ("ba", lambda v: ["--artifact", f"{FX}/{v}/story.md", "--repo", str(REPO)], {"BA-2", "BA-3", "BA-5", "BA-6", "BA-8", "BA-9"}),
    ("arch", lambda v: ["--artifact", f"{FX}/{v}/design.md", "--story", f"{FX}/good/story.md", "--repo", str(REPO)],
     {"AR-4", "AR-5", "AR-8", "AR-9", "AR-10", "AR-12", "AR-13"}),
    ("onboard", lambda v: ["--artifact", f"{FX}/{v}/pay-claude.md", "--repo", str(REPO), "--service", "pay-service"],
     {"OB-1", "OB-2", "OB-5", "OB-6"}),
    ("qa", lambda v: ["--results", f"{FX}/{v}/qa-results.json", "--story", f"{FX}/good/story.md", "--repo", str(REPO)],
     {"QA-1", "QA-2", "QA-3", "QA-4", "QA-5", "QA-7"}),
    ("sm", lambda v: ["--artifact", f"{FX}/{v}/standup.md", "--facts", f"{FX}/good/sprint-facts.json"], {"SM-3", "SM-6", "SM-7"}),
]


def bench(agent, args, out):
    r = subprocess.run(RUN + [agent, *args, "--out-dir", str(out), "--name", agent, "--quiet"], capture_output=True, text=True)
    try:
        rep = json.loads((Path(out) / f"{agent}-benchmark.json").read_text())
    except OSError:
        return r.returncode, None, set(), r.stderr[-300:]
    return r.returncode, rep["verdict"], {c["id"] for c in rep["checks"] if c["result"] == "FAIL"}, ""


def git(repo, *a):
    subprocess.run(["git", *a], cwd=repo, capture_output=True, check=True)


def scratch_repo(td):
    repo = Path(td) / "repo"
    shutil.copytree(REPO, repo)
    git(repo, "init", "-q", "-b", "develop")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


SVC = "services/pay-service"
RECEIPT = '''package x.pay.service;

import java.math.BigDecimal;

@Service
@RequiredArgsConstructor
public class ReceiptService {
    public String receipt(String id) {
        return "R-" + id;
    }
}
'''
TEST = "package x.pay.service;\nclass ReceiptServiceTest {}\n"


def reports(repo, failures=0):
    d = repo / SVC / "target/surefire-reports"
    d.mkdir(parents=True, exist_ok=True)
    fail = '<failure message="boom"/>' if failures else ""
    (d / "TEST-x.pay.service.ReceiptServiceTest.xml").write_text(
        f'<testsuite name="x" tests="3" failures="{failures}" errors="0" skipped="0">'
        f'<testcase classname="x.pay.service.ReceiptServiceTest" name="a">{fail}</testcase>'
        '<testcase classname="x.pay.service.ReceiptServiceTest" name="b"/><testcase classname="x.pay.service.ReceiptServiceTest" name="c"/></testsuite>')
    j = repo / SVC / "target/site/jacoco"
    j.mkdir(parents=True, exist_ok=True)
    (j / "jacoco.csv").write_text("GROUP,PACKAGE,CLASS,INSTRUCTION_MISSED,INSTRUCTION_COVERED,BRANCH_MISSED,BRANCH_COVERED,"
                                  "LINE_MISSED,LINE_COVERED\npay,x.pay.service,ReceiptService,1,9,0,0,1,9\n")


def main():
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        for agent, args, planted in CASES:
            rc_g, v_g, f_g, err = bench(agent, args("good"), Path(td) / f"{agent}-good")
            rc_b, v_b, f_b, err2 = bench(agent, args("bad"), Path(td) / f"{agent}-bad")
            ok = v_g == "PASS" and rc_g == 0 and v_b == "FAIL" and rc_b == 1 and f_b == planted
            fails += not ok
            print(f"{'ok ' if ok else 'FAIL'} {agent:8} good={v_g} bad={v_b} fails={sorted(f_b)}"
                  + ("" if ok else f"  expected {sorted(planted)} good-fails={sorted(f_g)} {err}{err2}"))

        # devops: the fixture's workflow is clean; adding the bad workflow must trip 5 checks
        _, v_g, _, _ = bench("devops", ["--repo", str(REPO)], Path(td) / "do-good")
        bad = Path(td) / "do-repo"
        shutil.copytree(REPO, bad)
        shutil.copy(FX / "bad/ci.yml", bad / ".github/workflows/bad.yml")
        _, v_b, f_b, _ = bench("devops", ["--repo", str(bad)], Path(td) / "do-bad")
        want = {"DO-2", "DO-4", "DO-5", "DO-7", "DO-8"}
        ok = v_g == "PASS" and f_b == want
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} devops   good={v_g} bad={v_b} fails={sorted(f_b)}" + ("" if ok else f"  expected {sorted(want)}"))

        # dev: good = new service + test + passing reports + coverage; bad = money as double + failing test + no test class
        for variant in ("good", "bad"):
            with tempfile.TemporaryDirectory() as t2:
                repo = scratch_repo(t2)
                git(repo, "checkout", "-qb", "feature")
                src = repo / SVC / "src/main/java/x/pay/service"
                src.mkdir(parents=True)
                body = RECEIPT if variant == "good" else RECEIPT.replace("public String receipt", "private double feeAmount;\n    public String receipt")
                (src / "ReceiptService.java").write_text(body)
                if variant == "good":
                    t = repo / SVC / "src/test/java/x/pay/service"
                    t.mkdir(parents=True)
                    (t / "ReceiptServiceTest.java").write_text(TEST)
                git(repo, "add", "-A")
                git(repo, "commit", "-qm", "change")
                reports(repo, failures=0 if variant == "good" else 1)
                _, v, f, err = bench("dev", ["--repo", str(repo), "--base", "develop"], Path(t2) / "out")
                want = set() if variant == "good" else {"DEV-1", "DEV-4", "DEV-6"}
                ok = f == want and v == ("PASS" if variant == "good" else "FAIL")
                fails += not ok
                print(f"{'ok ' if ok else 'FAIL'} dev/{variant:5} verdict={v} fails={sorted(f)}" + ("" if ok else f"  expected {sorted(want)} {err}"))
                if variant == "good":
                    # code-review on the same tree: + protected paths; editing CLAUDE.md must trip CR-1
                    _, v, f, _ = bench("code-review", ["--repo", str(repo), "--base", "develop"], Path(t2) / "cr")
                    (repo / "CLAUDE.md").write_text((repo / "CLAUDE.md").read_text() + "\n- relaxed\n")
                    git(repo, "commit", "-qam", "relax rules")
                    _, v2, f2, _ = bench("code-review", ["--repo", str(repo), "--base", "develop"], Path(t2) / "cr2")
                    ok = v == "PASS" and f2 == {"CR-1"}
                    fails += not ok
                    print(f"{'ok ' if ok else 'FAIL'} code-review clean={v} rulebook-edit fails={sorted(f2)}")

        # doc: moving the documented endpoint without updating openapi.yaml is a touched gap (DOC-2); untouched = PASS
        with tempfile.TemporaryDirectory() as t3:
            repo = scratch_repo(t3)
            _, v_g, f_g, _ = bench("doc", ["--repo", str(repo), "--base", "develop", "--service", "pay-service"], Path(t3) / "g")
            git(repo, "checkout", "-qb", "move")
            c = repo / SVC / "src/main/java/x/pay/web/PaymentController.java"
            c.write_text(c.read_text().replace('@GetMapping("/{id}")', '@GetMapping("/by-id/{id}")'))
            git(repo, "commit", "-qam", "move")
            _, v_b, f_b, _ = bench("doc", ["--repo", str(repo), "--base", "develop", "--service", "pay-service"], Path(t3) / "b")
            ok = v_g == "PASS" and f_b == {"DOC-2"}
            fails += not ok
            print(f"{'ok ' if ok else 'FAIL'} doc      unchanged={v_g} moved-endpoint fails={sorted(f_b)}"
                  + ("" if ok else f" good-fails={sorted(f_g)}"))
        # attacks found by the independent review: each must stay closed
        forged = Path(td) / "forged-qa.json"
        forged.write_text(json.dumps({"results": [
            {"ac": "r", "kind": "REST", "command": "curl x", "expected_status": 200, "http_status": 200,
             "response": json.dumps({"data": {}, "meta": {"timestamp": "t", "requestId": "r"}}), "verdict": "PASS"},
            {"ac": "EDGE: missing auth -> 401", "kind": "EDGE", "command": "curl x", "expected_status": 200,
             "http_status": 200, "response": "{}", "verdict": "PASS"}]}))
        _, v, f, _ = bench("qa", ["--results", str(forged), "--story", f"{FX}/good/story.md"], Path(td) / "forged")
        ok = {"QA-1", "QA-7"} <= f
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} attack: forged QA results (1 result for all ACs, 401 edge that got 200) -> {sorted(f)}")
        fake = Path(td) / "fake-claude.md"
        fake.write_text((FX / "good/pay-claude.md").read_text()
                        .replace("None (payments table is written by a script in this fixture).", "Payment:\n- id: UUID\n\nRefund:\n- id: UUID")
                        .replace("pay_schema — table `payments`.", "pay_schema — table `payments`, table `refund_ledger`.")
                        .replace("## 6. Redis Cache Keys Owned\nNone.", "## 6. Redis Cache Keys Owned\n| `pay:receipt:{id}` | 60s |")
                        .replace("## 8. REST Endpoints Called (Downstream Dependencies)\nNone.",
                                 "## 8. REST Endpoints Called (Downstream Dependencies)\n| ledger-service | GET /api/v1/ledger/{id} |"))
        _, v, f, _ = bench("onboard", ["--artifact", str(fake), "--repo", str(REPO), "--service", "pay-service"], Path(td) / "fake")
        want = {"OB-8c", "OB-9b", "OB-10b", "OB-11b"}
        ok = want <= f
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} attack: invented entity/table/redis key/downstream call -> {sorted(f & want)}"
              + ("" if ok else f" (all fails {sorted(f)})"))
        codes = []
        for agent, args in (("sm", ["--artifact", f"{FX}/good/standup.md"]),                      # no --facts
                            ("qa", ["--results", str(FX / "good/story.md")]),                      # not JSON
                            ("doc", ["--repo", str(REPO), "--service", "pay-service"]),           # no --base
                            ("onboard", ["--artifact", f"{FX}/good/pay-claude.md", "--repo", str(REPO), "--service", "nope"])):
            rc, *_ = bench(agent, args, Path(td) / f"usage-{agent}")
            codes.append(rc)
        ok = codes == [2, 2, 2, 2]
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} usage errors exit 2, never PASS/FAIL: {codes}")
        with tempfile.TemporaryDirectory() as t4:   # stale test reports (older than the change) must not count
            repo = scratch_repo(t4)
            git(repo, "checkout", "-qb", "f")
            reports(repo, failures=0)
            import os, time
            for f in (repo / SVC / "target").rglob("*"):
                os.utime(f, (time.time() - 3600, time.time() - 3600))
            src = repo / SVC / "src/main/java/x/pay/service"
            src.mkdir(parents=True)
            (src / "ReceiptService.java").write_text(RECEIPT)
            t = repo / SVC / "src/test/java/x/pay/service"
            t.mkdir(parents=True)
            (t / "ReceiptServiceTest.java").write_text(TEST)
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "c")
            _, v, f, _ = bench("dev", ["--repo", str(repo)], Path(t4) / "o")
            ok = "DEV-4" in f
            fails += not ok
            print(f"{'ok ' if ok else 'FAIL'} attack: stale surefire reports -> {sorted(f)}")
    total = len(CASES) + 9
    print(f"bench selftest: {total - fails}/{total}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
