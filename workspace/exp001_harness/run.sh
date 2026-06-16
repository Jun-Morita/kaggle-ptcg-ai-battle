#!/usr/bin/env bash
# Run a baseline gauntlet: random vs random.
set -euo pipefail
cd "$(dirname "$0")"
uv run python run_gauntlet.py "$@"
