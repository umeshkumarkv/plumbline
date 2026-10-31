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
  for a in $(grep -oE 'plumbline-[a-z]+(-[a-z]+)*' "$f" | sort -u | grep -vE '^plumbline-(drafts|policy-change|checks|prd-approved|dor-ready|hld-final|arch-approved|review-passed|qa-passed|test)$'); do
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
for h in '## Every run' '## Metrics' '## JIRA hand-off'; do
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
stale=( 'pl-approve' 'Separate approver' 'Run by:' '`Run by`' 'Context for the developer' 'All 13 sections' 'Feature tracker' 'info/exclude' 'dangerously-skip-permissions' 'run_in_background: true' 'features.md' 'context.md' 'changed since verified' )
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
v=$(grep -E '^[0-9]+\.[0-9]+\.[0-9]+' .github/plumbline/VERSION.md 2>/dev/null | head -1 | tr -d '[:space:]')
top=$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | cut -c4-)
[ -n "$v" ] && [ "$v" = "$top" ] && ok || bad ".github/plumbline/VERSION.md ('$v') must equal the top CHANGELOG version ('$top')"

# 7. Relative links in the docs resolve
for doc in README.md PILOT.md SECURITY.md RELEASING.md TEST-REPORT.md TEAM-TEST.md TEST-PLAN.md SMOKE-TEST.md eval/README.md; do
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

# 10. Templates: every template a command or agent names exists; the template checker passes a good draft and fails a bad one
for t in $(grep -rhoE 'templates/[a-z-]+\.md|`[a-z-]+\.md`' .claude | grep -oE '[a-z-]+\.md' | sort -u); do
  case "$t" in pl-*|plumbline-*|story-*|prd.md|design.md|epic.md|story.md|handoff-*|sprint-report.md) ;; *) continue;; esac
  case "$t" in pl-*|plumbline-*) continue;; esac
  [ -f ".github/plumbline/templates/$t" ] && ok || bad "a command names template '$t' that does not exist"
done
for t in .github/plumbline/templates/*.md; do
  case "$(basename "$t")" in README.md|CHANGELOG.md|claude-*.md) continue;; esac
  grep -q '^— Plumbline {{version}} · ' "$t" && ! grep -q '^## Record$' "$t" && ok || bad "$t: needs the '— Plumbline …' footer (no '## Record')"
done
bash tests/check-template.sh .github/plumbline/templates/handoff-dev.md tests/fixtures/handoff-dev.good.md >/dev/null \
  && ok || bad "check-template.sh fails a correct draft"
bash tests/check-template.sh .github/plumbline/templates/handoff-dev.md tests/fixtures/handoff-dev.bad.md >/dev/null \
  && bad "check-template.sh passes a broken draft" || ok
bash tests/check-template.sh .github/plumbline/templates/story.md tests/fixtures/story.business.md >/dev/null \
  && ok || bad "role check fails a business-only story"
bash tests/check-template.sh .github/plumbline/templates/story.md tests/fixtures/story.technical.md >/dev/null \
  && bad "role check passes a story with an API path and story points" || ok
for a in pm ba arch dev qa doc sm onboard; do
  f=.claude/agents/plumbline-$a-writer.md; [ -f "$f" ] || f=.claude/agents/plumbline-$a-runner.md
  grep -q '^## Your lane$' "$f" && ok || bad "$f: needs a '## Your lane' section"
done
for a in pm ba sm; do grep -qE '^tools: Read, (Grep, Glob, )?Write$' .claude/agents/plumbline-$a-writer.md && ok || bad "plumbline-$a-writer: read and write only (no Edit, no Bash)"; done

# 11. Template versions: every template has its name/version line, is in the lock with the same version and content,
#     and has a CHANGELOG entry — a template cannot change without its version going up
python3 - <<'PY' || fail=$((fail+1))
import glob, hashlib, os, re, sys
lock = {}
for l in open("tests/template-versions.txt"):
    if l.strip() and not l.startswith("#"): n, v, h = l.split(); lock[n] = (v, h)
log = open(".github/plumbline/templates/CHANGELOG.md").read()
errs = []
for t in sorted(glob.glob(".github/plumbline/templates/*.md")):
    n = os.path.basename(t)[:-3]
    if n in ("README", "CHANGELOG"): continue
    s = open(t, "rb").read()
    m = re.search(rb"<!-- plumbline:template ([a-z-]+) (v[0-9]+) -->", s)
    if not m or m.group(1).decode() != n: errs.append(f"{t}: needs <!-- plumbline:template {n} vN -->"); continue
    v = m.group(2).decode()
    if n not in lock: errs.append(f"{n}: not in tests/template-versions.txt — run bash tests/lock-templates.sh"); continue
    lv, lh = lock[n]
    if v == lv and hashlib.sha256(s).hexdigest() != lh:
        errs.append(f"{n} {v}: changed without a new version — bump it, add a CHANGELOG entry, run tests/lock-templates.sh")
    elif v != lv: errs.append(f"{n}: is {v}, lock says {lv} — run bash tests/lock-templates.sh")
    if v != "v1" and f"{n} {v}" not in log: errs.append(f"{n} {v}: no entry in templates/CHANGELOG.md")
for e in errs: print("FAIL:", e)
sys.exit(1 if errs else 0)
PY
checks=$((checks+1))

for pair in "claude-root:CLAUDE.md" "claude-unit:src/CLAUDE.md" "claude-reference:src/CLAUDE.reference.md"; do
  bash tests/check-template.sh ".github/plumbline/templates/${pair%%:*}.md" "eval/sample-app/${pair#*:}" >/dev/null \
    && ok || bad "eval sample ${pair#*:} does not match template ${pair%%:*}"
done

# Drafts never get committed: every command creates .plumbline-drafts/.gitignore (a 2.8.0 regression dropped it from four)
for f in .claude/commands/pl-*.md; do grep -q '\.plumbline-drafts/\.gitignore' "$f" && ok || bad "$f: must create .plumbline-drafts/.gitignore"; done
# Onboarding scans for secrets and checks every unit's reachability
grep -q 'Secrets scan' .claude/commands/pl-onboard.md && grep -q 'Reachable without that check' .github/plumbline/checklists/onboard-unit.md && grep -q 'no sampling' .github/plumbline/checklists/onboard-audit.md \
  && ok || bad "pl-onboard: needs the secrets scan and the reachability check"

# The framework is markdown only: nothing executable is ever copied into a project (2.8.12)
for f in $(git ls-files .claude .github/plumbline .github/agents .github/prompts); do
  case "$f" in *.md) ;; *) bad "$f: Plumbline installs markdown only — move it to tests/ or examples/" ;; esac
done; ok

# Only /pl-dev and /pl-code-review run git; every other command works on the folder (2.8.13)
for f in .claude/commands/pl-*.md; do
  case "$(basename "$f")" in pl-dev.md|pl-code-review.md) continue ;; esac
  grep -v 'every other command: `—`' "$f" | grep -qE '`(git|gh) [a-z]' && bad "$f: runs git/gh — only /pl-dev and /pl-code-review may" || ok
done

# Checklists a command hands to the judge by file must exist
for c in $(grep -ohE '\.github/plumbline/checklists/[a-z-]+\.md' .claude/commands/*.md | sort -u); do
  [ -f "$c" ] && ok || bad "a command names checklist $c that does not exist"; done

# 12. Every output a command posts names its template
while read -r c ts; do
  for t in $ts; do grep -q "\b$t\b" ".claude/commands/$c.md" && ok || bad "$c: never names its template $t"; done
done <<'MAP'
pl-pm prd.md epic.md
pl-ba story.md
pl-arch hld.md handoff-hld.md handoff-arch.md pr.md
pl-dev handoff-dev.md pr.md
pl-code-review handoff-review.md
pl-qa handoff-qa.md
pl-doc handoff-doc.md pr.md
pl-devops handoff-devops.md pr.md
pl-sm sprint-report.md sm-flag.md
pl-onboard claude-unit.md claude-reference.md claude-root.md pr.md
MAP

echo "Plumbline self-test: $((checks-fail))/$checks checks passed."
[ "$fail" -eq 0 ]
