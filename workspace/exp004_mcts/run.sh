#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run python train_mcts.py --generations "${1:-5}" --search-count "${2:-16}" --selfplay "${3:-40}" --eval "${4:-20}"
uv run python eval_vs_pool.py results/model_gen$(( ${1:-5} - 1 )).pth 20 "${2:-16}"
