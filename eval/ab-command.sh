#!/usr/bin/env bash
# A/B any Plumbline command on YOUR repository: same repo, same prompt, two Plumbline versions, headless.
# Measures what 2.7's "CLAUDE.md is the single source" claims to change: code-reading calls and tokens.
#   bash eval/ab-command.sh <refA> <refB> <path-to-your-repo> "<command line>"
#   e.g. bash eval/ab-command.sh v2.6.0 HEAD ~/work/broker-dealer "/pl-ba show today's orders and remaining daily limit"
# Your repo is copied to a temp folder for each run (never changed). It must already have its CLAUDE.md files
# (run /pl-onboard once and commit them). REPEAT=<n> repeats each version. MODEL=<model> picks the model.
# Nothing is posted: the prompt tells the run it is unattended and must not write to JIRA, Confluence or GitHub.
set -uo pipefail
EVAL=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$EVAL/.." && pwd)
A=${1:?refA}; B=${2:?refB}; REPO=$(cd "${3:?path to your repo}" && pwd); CMD=${4:?command line in quotes}
REPEAT=${REPEAT:-1}; model_arg=(); [ -n "${MODEL:-}" ] && model_arg=(--model "$MODEL")
base="$EVAL/results/ab-cmd-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$base"; tmp=$(mktemp -d)
for ref in "$A" "$B"; do
  safe=$(echo "$ref" | tr '/' '_')
  git -C "$ROOT" worktree add -q --detach "$tmp/pl-$safe" "$ref" || { echo "cannot check out $ref"; exit 1; }
  for n in $(seq 1 "$REPEAT"); do
    w="$tmp/repo-$safe-$n"; cp -R "$REPO" "$w"
    rm -rf "$w/.claude/commands/pl-"* "$w/.claude/agents/plumbline-"* "$w/.plumbline-drafts"
    mkdir -p "$w/.claude" "$w/.github"
    cp -R "$tmp/pl-$safe/.claude/commands" "$tmp/pl-$safe/.claude/agents" "$w/.claude/"
    [ -d "$tmp/pl-$safe/.github/plumbline" ] && cp -R "$tmp/pl-$safe/.github/plumbline" "$w/.github/"
    [ -f "$w/.claude/settings.json" ] || cp "$tmp/pl-$safe/examples/claude-settings.json" "$w/.claude/settings.json"
    echo "== $ref, run $n/$REPEAT"
    start=$(date +%s)
    ( cd "$w" && claude -p "$CMD — Non-interactive A/B run: nobody can answer questions; never write to JIRA, Confluence or GitHub." \
        --permission-mode default --output-format stream-json --verbose "${model_arg[@]}" > "$base/$safe-$n.jsonl" 2> "$base/$safe-$n.err" )
    echo $(( $(date +%s) - start )) > "$base/$safe-$n.secs"
  done
done
python3 - "$base" "$A" "$B" <<'PY'
import glob, json, sys, collections
base, refs = sys.argv[1], sys.argv[2:]
rows = ["| Version | Run | Read | Grep | Glob | Other tools | Input tokens (incl. cache) | Output tokens | Cost | Time | Verdict line |",
        "|---|---|---|---|---|---|---|---|---|---|---|"]
for ref in refs:
    safe = ref.replace("/", "_")
    for p in sorted(glob.glob(f"{base}/{safe}-*.jsonl")):
        n = p.rsplit("-", 1)[1][:-6]; tools = collections.Counter(); tin = tout = 0; res = {}; seen = set()
        for line in open(p):
            try: e = json.loads(line)
            except ValueError: continue
            if e.get("type") == "result": res = e
            m = e.get("message") or {}
            if e.get("type") == "assistant" and isinstance(m, dict):
                mid = m.get("id")
                u = m.get("usage") or {}
                if mid not in seen:
                    seen.add(mid)
                    tin += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                    tout += u.get("output_tokens", 0)
                for c in m.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use": tools[c.get("name")] += 1
        other = sum(v for k, v in tools.items() if k not in ("Read", "Grep", "Glob"))
        first = (res.get("result") or "NO RESULT").strip().splitlines()[0][:60] if res else "NO RESULT"
        secs = open(p[:-6] + ".secs").read().strip()
        rows.append(f"| {ref} | {n} | {tools['Read']} | {tools['Grep']} | {tools['Glob']} | {other} | {tin:,} | {tout:,} | "
                    f"${res.get('total_cost_usd', 0):.2f} | {secs}s | {first} |")
md = "\n".join(rows) + ("\n\nCounts include subagents when Claude Code streams their messages — check one .jsonl on your first run. Compare quality too: read both hand-overs before "
                        "calling the cheaper run better.\n")
open(f"{base}/ab-summary.md", "w").write(md); print(md); print("Results:", base)
PY
for d in "$tmp"/pl-*; do git -C "$ROOT" worktree remove --force "$d"; done
