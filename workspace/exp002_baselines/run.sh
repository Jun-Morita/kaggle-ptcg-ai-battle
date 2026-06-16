#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run python extract_policies.py
uv run python run_matchups.py "${1:-60}"
