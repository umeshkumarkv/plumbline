#!/usr/bin/env bash
# Builds a throwaway git repository for one eval case: branch `main` = the sample app + Plumbline,
# branch `case/<id>` = the change under review. Prints where it is and what to run.
#   bash eval/setup-case.sh <case-id> [target-dir]        e.g.  bash eval/setup-case.sh d1-email-search
set -euo pipefail
EVAL=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$EVAL/.." && pwd)
id=${1:?usage: setup-case.sh <case-id> [target-dir]}
case_dir="$EVAL/cases/$id"; [ -f "$case_dir/case.json" ] || { echo "no such case: $id (see eval/cases/)"; exit 1; }
dest=${2:-$(mktemp -d)/orderdesk-$id}
[ -e "$dest" ] && { echo "$dest already exists"; exit 1; }

mkdir -p "$dest" && cp -R "$EVAL/sample-app/." "$dest/"
mkdir -p "$dest/.claude" "$dest/.github"
cp -R "$ROOT/.claude/commands" "$ROOT/.claude/agents" "$dest/.claude/"
cp -R "$ROOT/.github/prompts" "$ROOT/.github/agents" "$dest/.github/"
cp "$ROOT/examples/claude-settings.json" "$dest/.claude/settings.json"
cd "$dest"
git init -q -b main
git add -A && git -c user.name=eval -c user.email=eval@example.com commit -qm "Order Desk baseline + Plumbline"
base=$(git rev-parse --short HEAD)
python3 - "$base" <<'PY'
import sys; p="src/CLAUDE.md"; s=open(p).read(); open(p,"w").write(s.replace("VERIFIED_COMMIT", sys.argv[1]))
PY
git -c user.name=eval -c user.email=eval@example.com commit -qam "docs: CLAUDE.md last updated at $base"
git switch -q -c "case/$id"

python3 - "$case_dir/case.json" <<'PY'
import json, os, sys
c = json.load(open(sys.argv[1]))
for e in c["edits"]:
    s = open(e["file"]).read()
    n = s.count(e["find"])
    if n != 1:
        sys.exit(f"edit for {e['file']} matches {n} times (must be exactly 1): {e['find'][:60]!r}")
    open(e["file"], "w").write(s.replace(e["find"], e["replace"]))
for path, content in c["new_files"].items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)
PY
title=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$case_dir/case.json")
git add -A && git -c user.name=dev -c user.email=dev@example.com commit -qm "$title"
git switch -q main

pr=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pr'])" "$case_dir/case.json")
cat <<EOF
Case $id ready in: $dest
  branch main      = baseline;  branch case/$id = the change ("$title")
Review it:
  Claude Code:  cd "$dest" && claude      then:  /pl-code-review case/$id
  Copilot:      open "$dest" in VS Code, Chat in Agent mode, runSubagent enabled, then:  /pl-code-review case/$id
  PR description to give if asked: $pr
Score it: save the review's final reply (or .plumbline-drafts/code-review*.md) to a file, then
  python3 "$EVAL/score.py" $id <review-file>
EOF
