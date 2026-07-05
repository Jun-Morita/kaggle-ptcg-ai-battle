#!/usr/bin/env bash
# Stage 2 launcher (see SESSION_NOTES.md "Stage 2 設計"). Launch manually, e.g.:
#   setsid nohup ./run_stage2.sh 2000 16 150 20 5 100000 80 > stage2.log 2>&1 < /dev/null &
#   disown
# Then monitor with: tail -f stage2.log
# Resumable: re-running the same command after an interruption picks up from
# the latest results/stage2/model_gen*.pth via --resume (replay buffer resets
# in-memory on restart, rebuilds over subsequent generations -- see SESSION_NOTES).
#
# 2026-07-06 update: added --replay-cap/--train-batches (sliding-window replay
# buffer, standard AlphaZero-style) after diagnosing the first Stage 2 run --
# value AUC did improve (0.49->0.63 over 21 gens) but each gen only trained on
# ~1000 fresh, then-discarded samples. User authorized a tens-of-hours GPU
# budget to let this run properly; default generations bumped 50->2000.
set -euo pipefail
cd "$(dirname "$0")"
GENERATIONS="${1:-2000}"
SEARCH_COUNT="${2:-16}"
SELFPLAY="${3:-150}"
EVAL="${4:-20}"
POOL_EVERY="${5:-5}"
REPLAY_CAP="${6:-100000}"
TRAIN_BATCHES="${7:-80}"
uv run python train_mcts.py \
  --generations "$GENERATIONS" --search-count "$SEARCH_COUNT" \
  --selfplay "$SELFPLAY" --eval "$EVAL" --deck charmq \
  --teacher pool --tag stage2 --pool-eval-every "$POOL_EVERY" --resume \
  --replay-cap "$REPLAY_CAP" --train-batches "$TRAIN_BATCHES"
