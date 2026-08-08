#!/usr/bin/env bash
# Capacity kept helping on the >=1075 subset when judged on ALL teachers
# (255 0.8002 / 511 0.8024 / 1023 0.8069), which is the opposite of what less
# data predicted. Extend the trend to 2047, then gate the best -- the held-out
# gap (+0.0045, ~530 decisions) is too small to ship on, and v5 already showed a
# top-k win reversing in real games.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== >=1075, 2047 leaves"
uv run python train_gbdt.py --rows v7 --min-score 1075 --leaves 2047 --rounds 900 \
    --out-tag q1075L2047 2>&1 | grep -v "LightGBM\]" | tail -8
echo "=== all on ONE held-out set (all teachers)"
uv run python eval_fixed.py --rows v7 \
    --tags v7m1075,q1075L1023,q1075L2047 2>&1 | grep -v "LightGBM\]"

echo "=== ship path for the 1023 variant"
uv run python export_pure.py --tag q1075L1023 2>&1 | tail -7
uv run python parity_pure.py --tag q1075L1023 --rows v7 --n 150 2>&1 | tail -4
uv run python build_submission.py --tag q1075L1023 --n 25 2>&1 | tail -10

A=build_q1075L1023/submission.tar.gz
echo "=== weighted field gate (baseline = build_v6 = v054)"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gr_alakazam.log 2>&1
printf "  alakazam   "; tail -1 gr_alakazam.log
uv run python eval_h2h.py --opp lucario --n 600 --artifact $A > gr_lucario.log 2>&1
printf "  lucario    "; tail -1 gr_lucario.log
for o in crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gr_$o.log 2>&1
  printf "  %-11s" $o; tail -1 gr_$o.log
done
echo "=== mirror: vs the shipped v6 build (v054), n=600"
uv run python eval_h2h.py --n 600 --artifact $A \
    --opp gbdt:build_v6/submission.tar.gz > h2h_L1023_vs_v6.log 2>&1
tail -1 h2h_L1023_vs_v6.log
echo "=== and directly against the 511 variant, n=600"
uv run python eval_h2h.py --n 600 --artifact $A \
    --opp gbdt:build_v7m1075/submission.tar.gz > h2h_L1023_vs_L511.log 2>&1
tail -1 h2h_L1023_vs_L511.log
echo "=== V11 DONE"
