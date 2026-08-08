#!/usr/bin/env bash
# v6 = the full teacher corpus (1,188,672 decisions vs v4's capped 700,012),
# built with 10 extra search/evolution features appended to the v4b row.
#
# Two models come out of ONE corpus build, because the new features were appended
# and the first 318 columns therefore ARE the v4b row:
#   v6s  full rows, 318 columns -> isolates CORPUS SIZE against v4b
#   v6   full rows, 336 columns -> adds the FEATURES on top of v6s
# Hyperparameters are v4b's throughout (511 leaves, lr 0.04, min_data 100).
set -u
cd "$(dirname "$0")"

echo "=== v6s train (corpus size only, 318 features)"
uv run python train_gbdt.py --rows v6 --n-feat 318 --out-tag v6s --rounds 900 \
    2>&1 | grep -v "LightGBM\]"

echo "=== v6 train (corpus size + 10 search/evolution features, 336)"
uv run python train_gbdt.py --rows v6 --out-tag v6 --rounds 900 \
    2>&1 | grep -v "LightGBM\]"

echo "=== V6 TRAIN DONE"
