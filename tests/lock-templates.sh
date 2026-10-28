#!/usr/bin/env bash
# Re-writes .github/plumbline/templates/VERSIONS after you changed a template ON PURPOSE:
#   1. bump that template's "<!-- plumbline:template <name> vN -->" line (v1 → v2),
#   2. add a "<name> vN" entry to .github/plumbline/templates/CHANGELOG.md (what changed, what readers must accept),
#   3. run: bash tests/lock-templates.sh   — then bash tests/validate.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import glob, hashlib, os, re
rows = []
for t in sorted(glob.glob(".github/plumbline/templates/*.md")):
    n = os.path.basename(t)[:-3]
    if n in ("README", "CHANGELOG"): continue
    s = open(t, "rb").read()
    m = re.search(rb"<!-- plumbline:template ([a-z-]+) v([0-9]+) -->", s)
    if not m or m.group(1).decode() != n: raise SystemExit(f"{t}: first line must be <!-- plumbline:template {n} vN -->")
    rows.append(f"{n} v{m.group(2).decode()} {hashlib.sha256(s).hexdigest()}")
open(".github/plumbline/templates/VERSIONS", "w").write(
    "# template version sha256 — written by tests/lock-templates.sh; checked by tests/validate.sh\n" + "\n".join(rows) + "\n")
print("\n".join(rows))
PY
