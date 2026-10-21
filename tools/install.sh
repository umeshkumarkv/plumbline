#!/bin/bash
# Kept for compatibility: the setup step is init.py (detect, project.yaml, install, baseline, doctor).
exec python3 "$(cd "$(dirname "$0")" && pwd)/init.py" "$@"
