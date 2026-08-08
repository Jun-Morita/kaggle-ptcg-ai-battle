#!/usr/bin/env bash
# Re-tune capacity for the >=1075 subset. The 511-leaf operating point was chosen
# at 284k training queries and re-confirmed at 481k; the >=1075 filter puts main
# back down to 248k, and capacity has already proven to be data-size dependent
# once in this experiment (63 was fine until it wasn't). Cheap to check.
#
# Rounds are FIXED here rather than early-stopped, because the threshold sweep's
# one weakness was that every model stopped on its own validation set -- so the
# comparison mixed "different data" with "different amount of fitting".
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for L in 255 511 1023; do
  echo "=== >=1075, $L leaves"
  uv run python train_gbdt.py --rows v7 --min-score 1075 --leaves $L --rounds 900 \
      --out-tag q1075L$L 2>&1 | grep -v "LightGBM\]" | tail -8
done
echo "=== all on ONE held-out set (all teachers)"
uv run python eval_fixed.py --rows v7 \
    --tags v7,v7m1075,q1075L255,q1075L511,q1075L1023 2>&1 | grep -v "LightGBM\]"
echo "=== V10 DONE"
