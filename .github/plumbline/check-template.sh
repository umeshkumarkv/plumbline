#!/usr/bin/env bash
# Plumbline template check — deterministic, no model. Is a draft written on its template?
#   bash .github/plumbline/check-template.sh <template> <draft>      exit 0 = PASS
# Checks: (1) every "## " heading of the template is in the draft, exactly and in the same order;
# (2) every "Label: {{…}}" field of the template appears in the draft as "Label: <value>" (or "- Label: <value>");
# (3) a hand-off comment's first line is "[Plumbline /pl-<role>] YYYY-MM-DD";
# (4) no "{{" placeholder is left; (5) no heading is left empty (write "None").
set -uo pipefail
t=${1:?usage: check-template.sh <template> <draft>}; d=${2:?usage: check-template.sh <template> <draft>}
[ -f "$t" ] || { echo "FAIL: no template $t"; exit 2; }
[ -f "$d" ] || { echo "FAIL: no draft $d"; exit 2; }
awk -v T="$t" -v D="$d" '
function trim(s) { sub(/[ \t\r]+$/, "", s); return s }
NR == FNR {
  line = trim($0)
  if (FNR == 1 && line ~ /^\[Plumbline \/pl-/) handoff = 1
  if (line ~ /^## /) heads[++nh] = line
  f = line; sub(/^[-*] /, "", f)
  if (f ~ /^[A-Z][A-Za-z ]*: \{\{/) { split(f, a, ": "); fields[++nf] = a[1] }
  next
}
{
  line = trim($0); gsub(/\\/, "", line)   # JIRA and Confluence escape [ ] ~ _ on read-back
  if (!started && line != "") { started = 1; first = line }
  if (line ~ /^## /) { dh[++nd] = line; if (prevhead != "" && !body) empty[prevhead] = 1; prevhead = line; body = 0 }
  else if (line != "") body = 1
  if (index(line, "{{")) { bad = bad sprintf("FAIL: placeholder left on line %d: %s\n", FNR, substr(line, 1, 80)) }
  f = line; sub(/^[-*] /, "", f)
  for (i = 1; i <= nf; i++) if (index(f, fields[i] ": ") == 1 && length(f) > length(fields[i]) + 2) have[fields[i]] = 1
}
END {
  if (prevhead != "" && !body) empty[prevhead] = 1
  if (handoff && first !~ /^\[Plumbline \/pl-[a-z-]+\] [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/)
    bad = bad "FAIL: first line must be \"[Plumbline /pl-<role>] YYYY-MM-DD\", got: " substr(first, 1, 80) "\n"
  j = 1
  for (i = 1; i <= nh; i++) {
    k = j
    while (k <= nd && dh[k] != heads[i]) k++
    if (k > nd) bad = bad "FAIL: heading missing or out of order: " heads[i] "\n"
    else { if (heads[i] in empty) bad = bad "FAIL: empty section (write None): " heads[i] "\n"; j = k + 1 }
  }
  for (i = 1; i <= nf; i++) if (!(fields[i] in have)) bad = bad "FAIL: field missing or empty: " fields[i] ":\n"
  if (bad != "") { printf "%s", bad; exit 1 }
  print "PASS: " D " matches " T
}' "$t" "$d"
