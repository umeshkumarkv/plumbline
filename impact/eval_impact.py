#!/usr/bin/env python3
"""Score impact.py against independently written scenarios and answer keys.

  eval_impact.py <clean_repo> <scenarios.json> <truth-a.json> <truth-b.json> <out_dir>

Ground truth = units BOTH judges list (agreed). Units only one judge lists are reported separately ("disputed")
and excluded from scoring, so neither judge's mistakes count for or against the tool.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import impact  # noqa: E402


def apply(clean: Path, sc: dict, dst: Path):
    shutil.copytree(clean, dst, ignore=shutil.ignore_patterns("node_modules", "target", ".git"))
    for e in sc["edits"]:
        f = dst / e["file"]
        t = f.read_text()
        assert t.count(e["find"]) == 1, (sc["id"], e["file"])
        f.write_text(t.replace(e["find"], e["replace"], 1))


def main():
    clean, scen, ta, tb, out = map(Path, sys.argv[1:6])
    out.mkdir(parents=True, exist_ok=True)
    S = json.loads(scen.read_text())
    A, B = json.loads(ta.read_text()), json.loads(tb.read_text())
    rows, tot = [], {"tp": 0, "fp": 0, "fn": 0, "disputed_hit": 0, "disputed_miss": 0}
    ctrl = {"n": 0, "clean": 0}
    base = Path(tempfile.mkdtemp()) / "base"
    shutil.copytree(clean, base, ignore=shutil.ignore_patterns("node_modules", "target", ".git"))
    for sc in S:
        sid = sc["id"]
        with tempfile.TemporaryDirectory() as td:
            head = Path(td) / "head"
            apply(clean, sc, head)
            res = impact.analyse(base, head)
            (out / f"{sid}.bundle.md").write_text(impact.bundle(res, head))
        pred = set(res["affected"])
        a, b = set(A[sid]["affected"]), set(B[sid]["affected"])
        agreed, disputed = a & b, (a ^ b)
        tp, fp, fn = pred & agreed, pred - agreed - disputed, agreed - pred
        tot["tp"] += len(tp); tot["fp"] += len(fp); tot["fn"] += len(fn)
        tot["disputed_hit"] += len(pred & disputed); tot["disputed_miss"] += len(disputed - pred)
        if not a and not b:
            ctrl["n"] += 1
            ctrl["clean"] += not pred
        rows.append({"id": sid, "kind": sc.get("kind"), "title": sc.get("title"), "unit": sc.get("unit"),
                     "predicted": sorted(pred), "agreed": sorted(agreed), "disputed": sorted(disputed),
                     "tp": sorted(tp), "fp": sorted(fp), "fn": sorted(fn), "breaking": res["breaking"],
                     "reasons": {k: [r["reason"] for r in v] for k, v in res["affected"].items()}})
    rec = tot["tp"] / max(1, tot["tp"] + tot["fn"])
    prec = tot["tp"] / max(1, tot["tp"] + tot["fp"])
    summary = {"scenarios": len(S), **tot, "recall": round(rec, 3), "precision": round(prec, 3),
               "controls": ctrl, "judge_agreement_units": sum(len(set(A[s]["affected"]) & set(B[s]["affected"])) for s in A),
               "judge_disputed_units": sum(len(set(A[s]["affected"]) ^ set(B[s]["affected"])) for s in A)}
    (out / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    for r in rows:
        flag = "ok " if not r["fp"] and not r["fn"] else "ERR"
        print(f"{flag} {r['id']} {r['kind']:14} pred={r['predicted']} agreed={r['agreed']}"
              f"{' disputed=' + str(r['disputed']) if r['disputed'] else ''}"
              f"{' FN=' + str(r['fn']) if r['fn'] else ''}{' FP=' + str(r['fp']) if r['fp'] else ''}")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
