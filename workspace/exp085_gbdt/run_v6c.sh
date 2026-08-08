#!/usr/bin/env bash
# Overnight: settle v6s-vs-v6, then re-test CAPACITY on the bigger corpus.
#
# Why capacity again. sweep_main.py found 511 leaves was the plateau, but it found
# that on 284k training queries. The v6 corpus has 481k, and the optimal capacity
# moves with the data -- 63 leaves was "enough" until it wasn't. Training is now
# ~150s per family, so this is the cheapest lever left.
#
# Why v6s and v6 are both carried forward. Their direct gap (0.553 vs 0.537 against
# v4b) is 5 games in 300 and decides nothing; step 1 settles it head to head, but
# both widths get the capacity treatment so the answer does not depend on a coin
# flip made at n=300.
set -u
cd "$(dirname "$0")"

echo "=== 1. v6s vs v6 head to head, n=400"
uv run python eval_h2h.py --n 400 --artifact build_v6s/submission.tar.gz \
    --opp gbdt:build_v6/submission.tar.gz > h2h_v6s_vs_v6.log 2>&1
tail -1 h2h_v6s_vs_v6.log

for L in 1023 2047; do
  echo "=== 2. train 318 features @ $L leaves"
  uv run python train_gbdt.py --rows v6 --n-feat 318 --leaves $L --rounds 900 \
      --out-tag v6sL$L 2>&1 | grep -v "LightGBM\]" | tail -8
  echo "=== 3. train 336 features @ $L leaves"
  uv run python train_gbdt.py --rows v6 --leaves $L --rounds 900 \
      --out-tag v6L$L 2>&1 | grep -v "LightGBM\]" | tail -8
done

echo "=== V6C TRAIN DONE"
