#!/usr/bin/env bash
# Teacher quality vs teacher quantity. The corpus now carries each teacher's
# ladder score, so a threshold costs a training run instead of a two-hour
# re-featurisation. Teachers are already all >=1000; row-level survival is
#   >=1050  85.9%   >=1100  46.5%   >=1150  15.3%
# v6 showed corpus SIZE is worth real winrate, so quality has to beat that loss.
#
# v7 with no threshold is trained FIRST as the control. It should reproduce v6's
# 0.7839; if it does not, the difference is the corpus rebuild (the teacher-score
# column) and not the threshold, and the rest of the sweep means nothing.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # $0 is "." when run as ./run_v7.sh

echo "=== v7 control (no threshold; must reproduce v6's 0.7839)"
uv run python train_gbdt.py --rows v7 --rounds 900 --out-tag v7 2>&1 | grep -v "LightGBM\]" | tail -8
for TH in 1050 1100 1150; do
  echo "=== v7 min-score $TH"
  uv run python train_gbdt.py --rows v7 --rounds 900 --min-score $TH \
      --out-tag v7m$TH 2>&1 | grep -v "LightGBM\]" | tail -8
done
echo "=== V7 TRAIN DONE"
