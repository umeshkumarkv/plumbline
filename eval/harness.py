#!/usr/bin/env python3
"""Plumbline Guardrails eval harness.

For each entry in defects.json (planted defects + benign controls):
  1. copy the clean repo, apply the mutation
  2. run the deterministic gates against the ratchet baseline -> caught if any NEW finding
  3. write a unified diff (with surrounding context) for blind critic review

  harness.py gates  <clean_repo> <defects.json> <outdir>   -> outdir/gates.json, outdir/diffs/<anon>.diff
  harness.py score  <defects.json> <outdir>                -> outdir/scorecard.json + .md

Diffs are written under anonymous ids (shuffled, seeded) so critics cannot infer defect vs control
from ids. The id map lives in outdir/key.json and is never given to critics.
"""
import difflib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATES = HERE.parent / "gates" / "run_gates.py"
BASELINE = HERE / "broker-dealer-baseline.json"   # the reference repository's debt (a project's own lives in .plumbline/gates/)


def apply(entry, repo: Path):
    target = repo / entry["file"]
    if entry["op"] == "new_file":
        before = ""
        target.parent.mkdir(parents=True, exist_ok=True)
        after = entry["content"]
    else:
        before = target.read_text()
        assert before.count(entry["find"]) == 1, f"{entry['id']}: find not unique"
        after = before.replace(entry["find"], entry["replace"])
    target.write_text(after)
    return before, after


def gates(clean: Path, defects_path: Path, out: Path):
    entries = json.loads(defects_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "diffs").mkdir(exist_ok=True)
    rng = random.Random(20261013)
    anon = [f"R{n:03d}" for n in rng.sample(range(100, 1000), len(entries))]
    key, results = {}, {}
    for entry, aid in zip(entries, anon):
        key[aid] = entry["id"]
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "repo"
            shutil.copytree(clean / "services", work / "services")
            diff = ""
            for edit in entry.get("edits", [entry]):
                before, after = apply({**edit, "id": entry["id"]}, work)
                diff += "".join(difflib.unified_diff(
                    before.splitlines(True), after.splitlines(True),
                    fromfile=f"a/{edit['file']}", tofile=f"b/{edit['file']}", n=12))
            (out / "diffs" / f"{aid}.diff").write_text(diff)
            r = subprocess.run([sys.executable, str(GATES), str(work), "--baseline", str(BASELINE), "--json", "--all-packs"],
                               capture_output=True, text=True)
            try:
                new = json.loads(r.stdout)["new"]
            except Exception:
                new = [{"rule": "HARNESS-ERROR", "path": entry["file"], "line": 0, "message": r.stderr[-300:]}]
        results[entry["id"]] = {"caught": bool(new), "diff_lines": diff.count("\n"), "rules": sorted({f["rule"] for f in new}),
                                "files": sorted({f["path"] for f in new})}
        print(f"{entry['id']:4} {'CAUGHT' if new else '  -   '} {','.join(results[entry['id']]['rules'])}")
    (out / "gates.json").write_text(json.dumps(results, indent=1))
    (out / "key.json").write_text(json.dumps(key, indent=1))


def score(defects_path: Path, out: Path):
    entries = {e["id"]: e for e in json.loads(defects_path.read_text())}
    g = json.loads((out / "gates.json").read_text())
    key = json.loads((out / "key.json").read_text())
    critic = {}
    for f in sorted((out / "critic").glob("*.json")):
        for aid, verdict in json.loads(f.read_text()).items():
            critic[key[aid]] = verdict
    rows, agg = [], {}
    for eid, e in entries.items():
        kind = e["kind"]
        gc = g[eid]["caught"]
        cv = critic.get(eid, {})
        cc = bool(cv.get("violation"))
        rows.append({"id": eid, "kind": kind, "category": e["category"], "gate": gc, "critic": cc,
                     "either": gc or cc, "gate_rules": g[eid]["rules"], "critic_reason": cv.get("rule", "")})
        a = agg.setdefault(kind, {"n": 0, "gate": 0, "critic": 0, "either": 0})
        a["n"] += 1; a["gate"] += gc; a["critic"] += cc; a["either"] += gc or cc
    defects = [r for r in rows if r["kind"] != "control"]
    controls = [r for r in rows if r["kind"] == "control"]
    tot = lambda rs, k: sum(r[k] for r in rs)
    summary = {
        "defects": len(defects), "controls": len(controls),
        "recall": {k: round(tot(defects, k) / len(defects), 3) for k in ("gate", "critic", "either")},
        "false_positive_rate_on_controls": {k: round(tot(controls, k) / len(controls), 3) for k in ("gate", "critic", "either")},
        "by_kind": agg, "critic_reviewed": len(critic),
    }
    (out / "scorecard.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    md = ["| Detector | Recall on 50 defects | False positives on 15 controls |", "|---|---|---|"]
    for k, label in (("gate", "Deterministic gates only"), ("critic", "Isolated LLM critic only"), ("either", "Gates + critic")):
        md.append(f"| {label} | {tot(defects, k)}/{len(defects)} ({summary['recall'][k]:.0%}) | {tot(controls, k)}/{len(controls)} |")
    md += ["", "| Kind | n | Gates | Critic | Both |", "|---|---|---|---|---|"]
    for kind, a in agg.items():
        md.append(f"| {kind} | {a['n']} | {a['gate']} | {a['critic']} | {a['either']} |")
    (out / "scorecard.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "gates":
        gates(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve())
    elif cmd == "score":
        score(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
