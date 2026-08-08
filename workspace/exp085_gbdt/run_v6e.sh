#!/usr/bin/env bash
# Seed ensemble on top of v6 (336 features, 511 leaves -- the settled operating
# point). Capacity is exhausted and the corpus is now the whole teacher pool, so
# variance reduction is the remaining cheap lever: LightGBM's feature_fraction
# 0.8 / bagging_fraction 0.8 make each seed a different sample of the same data.
#
# The merged scorer is 3x the trees, so tar size and per-move time are the two
# things that can veto this regardless of strength -- build+smoke checks both.
set -u
cd "$(dirname "$0")"
for s in 43 44; do
  echo "=== train seed $s"
  uv run python train_gbdt.py --rows v6 --rounds 900 --seed $s --out-tag v6_s$s \
      2>&1 | grep -v "LightGBM\]" | tail -8
done
echo "=== merge v6 + v6_s43 + v6_s44"
uv run python export_pure.py --tag v6e --tags v6,v6_s43,v6_s44 2>&1 | tail -8
echo "=== parity (vs the MEAN of the three boosters)"
uv run python parity_pure.py --tag v6e --tags v6,v6_s43,v6_s44 --rows v6 --n 150 2>&1 | tail -4
echo "=== build + smoke"
uv run python build_submission.py --tag v6e --n 25 2>&1 | tail -10
echo "=== V6E DONE"
