#!/usr/bin/env bash
# macOS/Linux shortcut for install.py (which also runs on Windows):  cd <your-project> && ~/plumbline/install.sh --jira KEY
set -euo pipefail
PY=$(command -v python3 || command -v python || true)
[ -n "$PY" ] || { echo "Python 3.10+ is required." >&2; exit 1; }
exec "$PY" "$(cd "$(dirname "$0")" && pwd)/install.py" "$@"
