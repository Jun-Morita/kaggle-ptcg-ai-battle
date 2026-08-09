#!/usr/bin/env bash
# Per-family capacity. All five families have shared one setting (511 leaves /
# lr 0.04 / min_data 100) that was tuned on `main` alone, and under it the small
# families stop almost at once:
#
#   main  247,933 train_q -> 143 trees
#   c7     80,430 ->  99      mid 187,789 -> 48
#   low    15,184 ->  27      easy 28,143 -> 14
#
# Two explanations fit: the family is genuinely easy and there is nothing left to
# learn, or 511 leaves overfits it within a few rounds and early stopping cuts in.
# Only a sweep separates them, and it is cheap -- the small families train in
# seconds.
#
# Every model is scored by eval_fixed.py on the SAME all-teacher held-out set, so
# families trained at different capacities stay comparable. Capacity chosen on
# held-out has already misled us once (511 -> 2047 improved held-out and LOST in
# real games), so whatever this picks goes through the field gate and the mirror
# before it can ship.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for L in 31 63 127 255; do
  echo "=== small families at $L leaves (main/c7 held at 511)"
  uv run python train_gbdt.py --rows v7 --min-score 1075 --rounds 900 \
      --leaves main=511,c7=511,mid=$L,low=$L,easy=$L \
      --out-tag s$L 2>&1 | grep -v "LightGBM\]" | tail -7
done

echo "=== all on ONE held-out set (all teachers)"
uv run python eval_fixed.py --rows v7 \
    --tags v7m1075,s31,s63,s127,s255 2>&1 | grep -v "LightGBM\]"
echo "=== V13 DONE"
