#!/usr/bin/env bash
# A/B: run the code-review eval on two Plumbline versions with the SAME cases and scorer, REPEAT times each.
#   bash eval/ab.sh <refA> <refB> [case-id ...]        e.g.  bash eval/ab.sh v2.6.0 HEAD
#   REPEAT=3 MODEL=<model> bash eval/ab.sh v2.6.0 HEAD
# Results: eval/results/ab-<timestamp>/<ref>-run<n>/ and a side-by-side ab-summary.md.
set -uo pipefail
EVAL=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$EVAL/.." && pwd)
A=${1:?usage: ab.sh <refA> <refB> [case-id ...]}; B=${2:?usage: ab.sh <refA> <refB> [case-id ...]}; shift 2
REPEAT=${REPEAT:-1}
base="$EVAL/results/ab-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$base"; wt=$(mktemp -d)
for ref in "$A" "$B"; do
  safe=$(echo "$ref" | tr '/' '_')
  git -C "$ROOT" worktree add -q --detach "$wt/$safe" "$ref" || { echo "cannot check out $ref"; exit 1; }
  for n in $(seq 1 "$REPEAT"); do
    echo "== $ref, run $n/$REPEAT"
    OUT="$base/$safe-run$n" PLUMBLINE_FROM="$wt/$safe" bash "$EVAL/run.sh" "$@" > "$base/$safe-run$n.log" 2>&1
    tail -3 "$base/$safe-run$n.log"
  done
done
python3 - "$base" "$A" "$B" <<'PY'
import glob, json, os, sys
base, refs = sys.argv[1], sys.argv[2:]
rows = ["| Version | Run | Recall | False alarms | Decoys flagged | Not scored | Cost |", "|---|---|---|---|---|---|---|"]
for ref in refs:
    safe = ref.replace("/", "_")
    for d in sorted(glob.glob(f"{base}/{safe}-run*/")):
        tf = tp = fa = dec = 0; cost = 0.0
        for p in glob.glob(f"{d}*.score.json"):
            s = json.load(open(p))
            if s["kind"] == "defects": tf += s["found"]; tp += s["planted"]; dec += s["decoys_flagged"]
            else: fa += s["false_alarms"]
        metas = glob.glob(f"{d}*.meta.json")
        cost = sum(json.load(open(m))["cost_usd"] for m in metas)
        ns = sum(1 for m in metas if json.load(open(m)).get("error"))
        rows.append(f"| {ref} | {os.path.basename(d.rstrip('/')).split('-run')[-1]} | {tf}/{tp} | {fa} | {dec} | {ns} | ${cost:.2f} |")
md = "\n".join(rows) + "\n\nOne run per version is anecdotal: use REPEAT=3 or more before drawing conclusions.\n"
open(f"{base}/ab-summary.md", "w").write(md); print(md); print("Results:", base)
PY
for d in "$wt"/*; do git -C "$ROOT" worktree remove --force "$d"; done
