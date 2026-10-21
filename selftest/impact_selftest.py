#!/usr/bin/env python3
"""Self-test for impact/: known changes on a two-service fixture must give known answers.

pay-service produces `payment.settled` (PaymentSettledEvent) and serves GET /api/v1/payments/{id} (PaymentView).
ledger-service consumes the topic via a Map (reads "amount") and calls the endpoint (reads `status`).
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impact"))
import impact  # noqa: E402

FIX = ROOT / "selftest" / "impact-fixture"
EV = "services/pay-service/src/main/java/x/pay/event/PaymentSettledEvent.java"
PROD = "services/pay-service/src/main/java/x/pay/kafka/PaymentProducer.java"
CTRL = "services/pay-service/src/main/java/x/pay/web/PaymentController.java"
VIEW = "services/pay-service/src/main/java/x/pay/web/PaymentView.java"
YML = "services/pay-service/src/main/resources/application.yml"

CASES = [  # (name, file, find, replace, expected affected, expect breaking)
    ("rename a field the consumer reads", EV, "amount;", "amountMinor;", {"ledger-service"}, False),
    ("rename a field nobody reads", EV, "currency;", "currencyCode;", set(), False),
    ("log message only", PROD, '"publishing payment {}"', '"sending {}"', set(), False),
    ("rename a response field the caller reads", VIEW, "status;", "state;", {"ledger-service"}, False),
    ("move the endpoint", CTRL, '@GetMapping("/{id}")', '@GetMapping("/by-id/{id}")', {"ledger-service"}, True),
    ("stop producing the topic", PROD, 'kafkaTemplate.send(TOPIC, "k", event);', "", {"ledger-service"}, True),
    ("change the port", YML, "port: 8091", "port: 8099", {"ledger-service"}, False),
    ("GET endpoint becomes POST (same path)", CTRL, '@GetMapping("/{id}")', '@PostMapping("/{id}")', {"ledger-service"}, True),
]


def main():
    fails = 0
    for name, f, find, repl, exp, exp_break in CASES:
        with tempfile.TemporaryDirectory() as td:
            head = Path(td) / "head"
            shutil.copytree(FIX, head)
            p = head / f
            t = p.read_text()
            assert t.count(find) == 1, (name, find)
            p.write_text(t.replace(find, repl))
            r = impact.analyse(FIX, head)
        got, brk = set(r["affected"]), bool(r["breaking"])
        ok = got == exp and brk == exp_break
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} {name:42} affected={sorted(got)} breaking={brk}"
              + ("" if ok else f"  (expected {sorted(exp)} breaking={exp_break})"))
    # git mode through the CLI, as CI runs it: a moved endpoint must exit 1 with --fail-on-breaking
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        shutil.copytree(FIX, repo)
        g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)
        g("init", "-q", "-b", "develop"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("add", "-A"); g("commit", "-qm", "base"); g("checkout", "-qb", "feature")
        c = repo / CTRL
        c.write_text(c.read_text().replace('@GetMapping("/{id}")', '@GetMapping("/by-id/{id}")'))
        g("commit", "-qam", "move endpoint")
        cache = Path(td) / "cache"
        cmd = [sys.executable, str(ROOT / "impact/impact.py"), "--repo", str(repo), "--base", "develop",
               "--cache", str(cache), "--fail-on-breaking"]
        r1 = subprocess.run(cmd, capture_output=True, text=True)
        r2 = subprocess.run(cmd, capture_output=True, text=True)   # second run: served from the cache
        ok = r1.returncode == 1 and "ledger-service" in r1.stdout and r2.stdout == r1.stdout and any(cache.iterdir())
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} git mode + cache + --fail-on-breaking      rc={r1.returncode} {r1.stdout.strip()[:90]}")
        # moving a service folder (same application name, same contracts) changes nothing for anyone
        g("checkout", "-q", "develop"); g("checkout", "-qb", "move")
        g("mv", "services/pay-service", "services/payments")
        g("commit", "-qm", "move folder")
        r3 = subprocess.run(cmd, capture_output=True, text=True)
        ok = r3.returncode == 0 and "-> affected -" in r3.stdout
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} moving a service folder is not a change       rc={r3.returncode} {r3.stdout.strip()[:80]}")
        # a .gitattributes encoding rule must not change what the map sees (cache poisoning guard)
        g("checkout", "-q", "develop"); g("checkout", "-qb", "attrs")
        (repo / ".gitattributes").write_text("services/pay-service/**/*.java working-tree-encoding=UTF-16LE\n")
        g("add", ".gitattributes"); g("commit", "-qm", "attrs")
        g("rm", "-rq", "--cached", "services"); g("checkout", "-q", "--", ".")   # re-checkout with the attribute
        g("reset", "-q", "--hard")
        sys.path.insert(0, str(ROOT / "impact"))
        import depmap
        clean = depmap.build(repo, None, "develop")["services"]["pay-service"]
        poisoned_cache = Path(td) / "cache2"
        attrs = depmap.build(repo, poisoned_cache, "HEAD")["services"]["pay-service"]
        ok = (len(attrs["kafka"]), len(attrs["provides"])) == (len(clean["kafka"]), len(clean["provides"])) == (1, 1)
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} .gitattributes re-encoding cannot hide contracts  kafka={len(attrs['kafka'])} provides={len(attrs['provides'])}")
    # a runtime path segment that lines up only with fixed endpoints is reported as a suspect call
    import depmap
    with tempfile.TemporaryDirectory() as td:
        head = Path(td) / "head"
        shutil.copytree(FIX, head)
        c = head / CTRL
        c.write_text(c.read_text().replace('@GetMapping("/{id}")', '@GetMapping("/latest")'))
        edges = [e for e in depmap.build(head, None, None)["rest_edges"] if e["from"] == "ledger-service"]
        ok = any(e["confidence"] == "suspect" for e in edges)
        fails += not ok
        print(f"{'ok ' if ok else 'FAIL'} runtime segment vs fixed endpoint -> suspect   {[e['confidence'] for e in edges]}")
    total = len(CASES) + 4
    print(f"impact selftest: {total - fails}/{total}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
