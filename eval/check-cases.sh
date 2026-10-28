#!/usr/bin/env bash
# Checks the eval material itself: every case must apply and compile, and every clean case's tests must pass.
# Needs Java 21 and Maven (network for the first run). ~3-6 min.   bash eval/check-cases.sh
set -uo pipefail
EVAL=$(cd "$(dirname "$0")" && pwd); W=$(mktemp -d); bad=0
for c in $(ls "$EVAL/cases"); do
  bash "$EVAL/setup-case.sh" "$c" "$W/$c" > /dev/null || { echo "FAIL  $c: case does not apply"; bad=1; continue; }
  ( cd "$W/$c" && git switch -q "case/$c" && mvn -B -q test > "$W/$c.log" 2>&1 ); rc=$?
  kind=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['kind'])" "$EVAL/cases/$c/case.json")
  if grep -q "COMPILATION ERROR" "$W/$c.log"; then echo "FAIL  $c: does not compile — see $W/$c.log"; bad=1
  elif [ "$kind" = clean ] && [ $rc -ne 0 ]; then echo "FAIL  $c: clean case, tests fail — see $W/$c.log"; bad=1
  else echo "ok    $c ($kind, mvn test exit $rc)"; fi
done
( cd "$W/$(ls "$EVAL/cases" | head -1)" && git switch -q main && mvn -B -q test > "$W/baseline.log" 2>&1 ) \
  && echo "ok    baseline (main) tests pass" || { echo "FAIL  baseline tests — see $W/baseline.log"; bad=1; }
[ $bad -eq 0 ] && echo "All cases OK." || echo "Some cases need fixing (logs in $W)."
exit $bad
