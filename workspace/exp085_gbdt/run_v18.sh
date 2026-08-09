#!/usr/bin/env bash
# A/B on DATA ONLY. Featuriser is byte-identical to v8 (360 columns); the single
# variable is which teacher days are in the corpus, and whether the absolute
# score filter is applied.
#
#   A  38 days, no filter    -- maximum exposure to the 07-30..08-08 meta
#   B  38 days, >= 1075      -- v055's criterion. Note this is NOT "top players":
#                               the pool's score level fell, so 1075 keeps 79% of
#                               07-28 seats but only 29% of 08-08 seats. It is a
#                               recency filter in disguise.
# C (28 days, no filter) needs no run: results/gbdt_v8 already is it.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
L="main=511,c7=255,mid=127,low=63,easy=31"
echo "=== A: v9 all"
uv run python train_gbdt.py --rows v9 --rounds 900 --out-tag v9a --leaves "$L" --seed 0 \
    > train_v9a.log 2>&1; grep -E "train_q|overall" train_v9a.log
echo "=== B: v9 >=1075"
uv run python train_gbdt.py --rows v9 --rounds 900 --out-tag v9b --leaves "$L" --seed 0 \
    --min-score 1075 > train_v9b.log 2>&1; grep -E "train_q|overall" train_v9b.log
echo "=== TRAIN DONE"
