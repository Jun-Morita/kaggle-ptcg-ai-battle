#!/usr/bin/env bash
# Track A to a decision. Three things, strictly sequential so no two CPU-heavy
# jobs overlap -- the 1.621s max_move that scared us was measured while
# near_deck.py was reading 4,800 episodes on the same box, and max_move is a
# maximum, i.e. exactly the statistic that contention corrupts.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== 1. index 08-09 (needed for track B)"
./scan_new_days.sh 2>&1 | tail -3

echo "=== 2. v10r vs the SHIPPED v056 build, n=1600 (clean box)"
uv run python eval_h2h.py --n 1600 --artifact build_v10r/submission.tar.gz \
    --opp gbdt:build_v9b/submission.tar.gz > h2h_v10r_vs_v9b.log 2>&1
tail -1 h2h_v10r_vs_v9b.log

echo "=== 3. lighter retrain (main 511->255, c7 255->127)"
uv run python train_gbdt.py --rows v10r --rounds 900 --out-tag v10rL \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 --seed 0 > train_v10rL.log 2>&1
grep -E "train_q|overall" train_v10rL.log
uv run python export_pure.py --tag v10rL 2>&1 | tail -2
uv run python parity_pure.py --tag v10rL --rows v10r --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v10rL --n 25 2>&1 | tail -5
echo "=== 4. lighter build vs v056, n=1600"
uv run python eval_h2h.py --n 1600 --artifact build_v10rL/submission.tar.gz \
    --opp gbdt:build_v9b/submission.tar.gz > h2h_v10rL_vs_v9b.log 2>&1
tail -1 h2h_v10rL_vs_v9b.log
echo "=== V24 DONE"
