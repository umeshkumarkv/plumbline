#!/usr/bin/env bash
# Plumbline self-test: structural checks on the framework's own files. No network, no model calls.
# Run from the repository root:  bash tests/validate.sh      (exit 0 = all checks passed)
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0; checks=0
ok()  { checks=$((checks+1)); }
bad() { checks=$((checks+1)); fail=$((fail+1)); echo "FAIL: $*"; }

CMDS=$(ls .claude/commands/pl-*.md | xargs -n1 basename | sed 's/\.md$//')
AGENTS=$(ls .claude/agents/plumbline-*.md | xargs -n1 basename | sed 's/\.md$//')

# 1. Every command: frontmatter, required sections, a judge, a hand-over, size budget
for c in $CMDS; do
  f=.claude/commands/$c.md
  head -1 "$f" | grep -qx -- '---' && grep -q '^description: Plumbline — ' "$f" && grep -q '^argument-hint: ' "$f" \
    && ok || bad "$f: frontmatter needs description (starting 'Plumbline — ') and argument-hint"
  for s in '## Every run' '## Metrics'; do grep -qx "$s" "$f" && ok || bad "$f: missing section '$s'"; done
  grep -q 'plumbline-judge' "$f" && ok || bad "$f: never starts plumbline-judge"
  grep -qiE '^## Step [0-9]+ — (Hand over|Report|Summary)' "$f" && ok || bad "$f: no hand-over/report/summary step"
  n=$(wc -l < "$f"); [ "$n" -le 140 ] && ok || bad "$f: $n lines (budget 140) — long commands are followed less reliably"
  # every agent a command names must exist
  for a in $(grep -oE 'plumbline-[a-z]+(-[a-z]+)*' "$f" | sort -u | grep -vE '^plumbline-(drafts|policy-change|checks|prd-approved|dor-ready|arch-approved|test)$'); do
    [ -f ".claude/agents/$a.md" ] && ok || bad "$f: names agent '$a' that does not exist"
  done
done

# 2. Copilot pointers: one per command and per agent, pointing at the right file, no orphans
for c in $CMDS; do
  p=.github/prompts/$c.prompt.md
  [ -f "$p" ] && grep -q "\.claude/commands/$c\.md" "$p" && ok || bad "$p: missing or not pointing at .claude/commands/$c.md"
done
for a in $AGENTS; do
  p=.github/agents/$a.agent.md
  [ -f "$p" ] && grep -q "\.claude/agents/$a\.md" "$p" && grep -q '^user-invocable: false' "$p" && ok \
    || bad "$p: missing, not pointing at .claude/agents/$a.md, or user-invocable"
  head -1 ".claude/agents/$a.md" | grep -qx -- '---' && grep -q "^name: $a$" ".claude/agents/$a.md" && grep -q '^tools: ' ".claude/agents/$a.md" \
    && ok || bad ".claude/agents/$a.md: frontmatter needs name: $a and tools"
done
for p in .github/prompts/*.prompt.md; do c=$(basename "$p" .prompt.md); [ -f ".claude/commands/$c.md" ] && ok || bad "$p: orphan (no .claude/commands/$c.md)"; done
for p in .github/agents/*.agent.md; do a=$(basename "$p" .agent.md); [ -f ".claude/agents/$a.md" ] && ok || bad "$p: orphan (no .claude/agents/$a.md)"; done

# 3. Shared blocks must be identical in every command that has them (they drift otherwise)
block() { awk -v h="$2" '$0==h{p=1;print;next} p&&/^## /{exit} p' "$1"; }
for h in '## Every run' '## Metrics' '## Feature tracker'; do
  ref=""; reff=""
  for c in $CMDS; do
    f=.claude/commands/$c.md; grep -qx "$h" "$f" || continue
    b=$(block "$f" "$h")
    if [ -z "$ref" ]; then ref=$b; reff=$f; ok
    elif [ "$b" = "$ref" ]; then ok
    else bad "$f: '$h' differs from $reff"; diff <(echo "$ref") <(echo "$b") | head -6; fi
  done
done

# 4. Stale or forbidden text
hits=$(grep -rnE '(^|[ `(])/plumbline-(onboard|pm|ba|arch|dev|qa|doc|devops|sm|code-review)([^-a-z]|$)' .claude .github README.md PILOT.md 2>/dev/null)
[ -z "$hits" ] && ok || bad "old /plumbline-<role> command names (now /pl-<role>): $hits"
stale=( 'info/exclude' 'dangerously-skip-permissions' 'run_in_background: true' )
for s in "${stale[@]}"; do
  hits=$(grep -rlF -- "$s" .claude .github README.md PILOT.md 2>/dev/null)
  [ -z "$hits" ] && ok || bad "stale text '$s' in: $hits"
done
grep -rnE '\bgit -C\b' .claude | grep -v 'never `git -C`' >/dev/null && bad ".claude uses 'git -C' outside the rule forbidding it" || ok

# 5. Example settings: valid, no rule both allowed and denied, dangerous git denied, push asks
python3 - <<'PY' || fail=$((fail+1))
import json,sys
d=json.load(open("examples/claude-settings.json"))["permissions"]
a,de,ask=set(d.get("allow",[])),set(d.get("deny",[])),set(d.get("ask",[]))
errs=[]
if a&de: errs.append(f"rules both allowed and denied: {sorted(a&de)}")
for need in ["Bash(git reset:*)","Bash(git checkout:*)","Bash(git clean:*)","Bash(git branch -D:*)","Bash(git -C:*)","Read(**/.env)","Edit(.claude/**)"]:
    if need not in de: errs.append(f"deny is missing {need}")
if "Bash(git push:*)" not in ask: errs.append("git push must be in ask")
for r in a:
    if r.startswith("Bash(git branch:") or r=="Bash(git:*)": errs.append(f"allow is too broad: {r}")
for e in errs: print("FAIL: examples/claude-settings.json:", e)
sys.exit(1 if errs else 0)
PY
checks=$((checks+1))

# 6. Version: VERSION file = top CHANGELOG entry
v=$(cat .github/plumbline/VERSION 2>/dev/null | tr -d '[:space:]')
top=$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | cut -c4-)
[ -n "$v" ] && [ "$v" = "$top" ] && ok || bad ".github/plumbline/VERSION ('$v') must equal the top CHANGELOG version ('$top')"

# 7. Relative links in the docs resolve
for doc in README.md PILOT.md SECURITY.md RELEASING.md TEST-REPORT.md TEAM-TEST.md eval/README.md; do
  [ -f "$doc" ] || continue
  for l in $(grep -oE '\]\([^)#:]+\)' "$doc" | sed -E 's/^\]\(//; s/\)$//'); do
    [ -e "$(dirname "$doc")/$l" ] && ok || bad "$doc: broken link '$l'"
  done
done

# 8. Workflows parse
python3 - <<'PY' || fail=$((fail+1))
import glob,sys
try:
    import yaml
except ImportError:
    print("note: PyYAML not installed — workflow syntax not checked"); sys.exit(0)
bad=0
for p in glob.glob(".github/workflows/*.yml"):
    try: yaml.safe_load(open(p))
    except Exception as e: print("FAIL:", p, e); bad=1
sys.exit(bad)
PY
checks=$((checks+1))

# 9. Eval set: every case is well-formed and applies cleanly to the sample app
if [ -d eval/cases ]; then
  tmp=$(mktemp -d)
  for d in eval/cases/*/; do
    c=$(basename "$d")
    python3 -c "import json,sys;c=json.load(open(sys.argv[1]));assert c['kind'] in ('clean','defects') and c['edits'] or c['new_files']" "$d/case.json" 2>/dev/null \
      && ok || bad "eval/cases/$c/case.json is malformed"
    if grep -q '"kind": "defects"' "$d/case.json"; then
      python3 -c "import json,sys;a=json.load(open(sys.argv[1]));assert a['defects'] and all(x['files'] and x['keywords'] for x in a['defects'])" "$d/answer.json" 2>/dev/null \
        && ok || bad "eval/cases/$c/answer.json missing or malformed"
    fi
    bash eval/setup-case.sh "$c" "$tmp/$c" > /dev/null 2>&1 && ok || bad "eval case $c does not apply to the sample app"
  done
  rm -rf "$tmp"
fi

echo "Plumbline self-test: $((checks-fail))/$checks checks passed."
[ "$fail" -eq 0 ]
