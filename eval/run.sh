#!/usr/bin/env bash
# Runs /pl-code-review headless (Claude Code) on every eval case, with the recommended permission settings,
# and scores each review.   bash eval/run.sh [case-id ...]      Results: eval/results/<timestamp>/
# Optional: MODEL=<model> to choose the model (default: Claude Code's default).
set -uo pipefail
EVAL=$(cd "$(dirname "$0")" && pwd)
cases=${*:-$(ls "$EVAL/cases")}
out="$EVAL/results/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$out"; W=$(mktemp -d)
model_arg=(); [ -n "${MODEL:-}" ] && model_arg=(--model "$MODEL")
for c in $cases; do
  bash "$EVAL/setup-case.sh" "$c" "$W/$c" > /dev/null || { echo "setup failed: $c"; continue; }
  pr=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pr'])" "$EVAL/cases/$c/case.json")
  start=$(date +%s)
  ( cd "$W/$c" && claude -p "/pl-code-review case/$c — PR description from the author: '$pr' Non-interactive run: nobody can answer questions; do not post anywhere." \
      --permission-mode default --output-format stream-json --verbose "${model_arg[@]}" > "$out/$c.jsonl" 2> "$out/$c.err" )
  secs=$(( $(date +%s) - start ))
  python3 - "$out/$c.jsonl" "$out/$c.review.md" "$secs" <<'PY'
import json, sys
res = [json.loads(l) for l in open(sys.argv[1]) if '"type":"result"' in l]
r = res[-1] if res else {}
open(sys.argv[2], "w").write(r.get("result", "NO RESULT"))
model = next((json.loads(l).get("model") for l in open(sys.argv[1]) if '"subtype":"init"' in l), "?")
json.dump({"cost_usd": round(r.get("total_cost_usd", 0), 3), "seconds": int(sys.argv[3]), "model": model},
          open(sys.argv[2] + ".meta.json", "w"))
PY
  python3 "$EVAL/score.py" "$c" "$out/$c.review.md" --json > "$out/$c.score.json"
  python3 "$EVAL/score.py" "$c" "$out/$c.review.md"
done
python3 - "$out" <<'PY'
import glob, json, os, sys
out = sys.argv[1]; rows = []; tf = tp = fa = dec = 0; cost = 0.0
for p in sorted(glob.glob(f"{out}/*.score.json")):
    s = json.load(open(p)); c = s["case"]; m = json.load(open(f"{out}/{c}.review.md.meta.json"))
    cost += m["cost_usd"]
    if s["kind"] == "defects":
        tf += s["found"]; tp += s["planted"]; dec += s["decoys_flagged"]
        res = f"{s['found']}/{s['planted']} found" + (f", decoy flagged" if s["decoys_flagged"] else "")
    else:
        fa += s["false_alarms"]; res = f"{s['false_alarms']} false alarms, {s['findings_minor']} minor"
    rows.append(f"| {c} | {s['kind']} | {s['verdict']} | {res} | {m['seconds']}s | ${m['cost_usd']} | {m['model']} |")
md = ["| Case | Kind | Verdict | Result | Time | Cost | Model |", "|---|---|---|---|---|---|---|", *rows, "",
      f"**Recall:** {tf}/{tp} planted defects found. **False alarms:** {fa} blocker/major findings on clean changes. "
      f"**Decoys flagged:** {dec}. **Total cost:** ${cost:.2f}."]
open(f"{out}/summary.md", "w").write("\n".join(md) + "\n"); print("\n".join(md)); print(f"\nResults: {out}")
PY
