#!/usr/bin/env bash
# Counter-strategy for the one matchup the gate and the ladder agree we lose.
#
#   cell         gate (n0814)   ladder (v061)   08-15 field
#   mixed_ex4       0.514        0.20 (1-4)        12.8%   <- worst on both
#   dragapult       0.865        0.75 (3-1)        34.2%   <- our best
#
# The corpus is already winners-only (build_rows drops any seat whose reward is
# not 1), so "learn from games we won" is the existing design. What has never
# been tried is learning harder from the games we won AGAINST THIS DECK.
#
# Not the same as --opp-mix, which was rejected at z -3.06 on 08-14. That bent the
# whole opponent distribution to the field, inflating dragapult from 3.7% to 25.8%
# and effectively deleting data. This moves one archetype and leaves the rest at
# 1.0, so the corpus keeps its size.
#
# Upside if it works: mixed_ex4 carries gate weight 0.16, so 0.514 -> 0.60 is
# +0.014, which would put n0814's 0.6604 at 0.674 -- past the v059 bar for the
# first time in eight attempts.
#
# Two strengths, because the right amount is unknown and over-weighting is the
# failure mode --opp-mix demonstrated.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for K in 3 6; do
  TAG="x4b$K"
  echo "=== $TAG : n0814 corpus, mixed_ex4 rows x$K"
  uv run python train_gbdt.py --rows n0814 --rounds 900 --out-tag "$TAG" --seed 0 \
      --leaves main=255,c7=127,mid=127,low=63,easy=31 --boost-opp "3:$K" \
      > "train_${TAG}.log" 2>&1
  grep -E "boosting|rows boosted|^  main |overall" "train_${TAG}.log"
  uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
  uv run python parity_pure.py --tag "$TAG" --rows n0814 --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -6

  echo "  --- frozen gate (bar: v059 = 0.6640, control: n0814 = 0.6604)"
  A="build_$TAG/submission.tar.gz"
  r() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }
  # the boosted cell first: if it has not moved, the rest is not worth measuring
  r --n 1200 --artifact "$A" --opp gbdt:build_ex4b/submission.tar.gz > "gg_${TAG}_ex4.log" 2>&1
  printf "  mixed_ex4   "; tail -1 "gg_${TAG}_ex4.log"
  r --opp ref --n 1200 --artifact "$A" > "gg_${TAG}_mirror.log" 2>&1
  printf "  mirror(ref) "; tail -1 "gg_${TAG}_mirror.log"
  r --opp alakazam --n 800 --artifact "$A" > "gg_${TAG}_alakazam.log" 2>&1
  printf "  alakazam    "; tail -1 "gg_${TAG}_alakazam.log"
  r --opp lucario --n 400 --artifact "$A" > "gg_${TAG}_lucario.log" 2>&1
  printf "  lucario     "; tail -1 "gg_${TAG}_lucario.log"
  for o in crustle dragapult; do
    r --opp $o --n 200 --artifact "$A" > "gg_${TAG}_$o.log" 2>&1
    printf "  %-11s " $o; tail -1 "gg_${TAG}_$o.log"
  done
  uv run python gate_score.py "$TAG"
  echo "=== $TAG DONE"
done
echo "=== EX4BOOST DONE"
