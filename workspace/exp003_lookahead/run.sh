#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run python eval_lookahead.py "${1:-30}"
