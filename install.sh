#!/usr/bin/env bash
# Install or upgrade Plumbline in the git repository you are standing in.
#   git clone https://github.com/umeshkumarkv/plumbline ~/plumbline
#   cd <your-project> && ~/plumbline/install.sh [init.py flags, e.g. --domain broker-dealer --ci]
# Fresh repo → copies .plumbline/ and runs init.py. Existing install (.plumbline/ or the older .agentic-sdlc/) →
# upgrade, keeping project.yaml and the baseline.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "Run this from inside your project's git repository." >&2; exit 1; }
[ "$TARGET" = "$SRC" ] && { echo "Run this from your project, not from the plumbline checkout." >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 "$SRC/tools/make_kit.py" --out "$TMP/kit" >/dev/null
cd "$TARGET"
if [ -d .plumbline/loops ] || [ -d .agentic-sdlc ]; then
  echo "Upgrading Plumbline in $TARGET to $(cat "$SRC/VERSION")"
  tar -czf "$TMP/plumbline.tar.gz" -C "$TMP/kit" .plumbline
  mkdir -p .plumbline && cp "$TMP/kit/.plumbline/init.py" .plumbline/init.py
  python3 .plumbline/init.py --upgrade "$TMP/plumbline.tar.gz" "$@"
else
  echo "Installing Plumbline $(cat "$SRC/VERSION") in $TARGET"
  cp -R "$TMP/kit/.plumbline" .plumbline
  python3 .plumbline/init.py "$@"
fi
