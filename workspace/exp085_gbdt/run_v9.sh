#!/usr/bin/env bash
# Ship path + weighted field gate for the teacher-quality winner (>=1075).
#
# Held-out, judged on the same 118,681 decisions from the WHOLE teacher
# population: 0.7836 (all teachers) -> 0.8024 (>=1075), every family up, c7
# +0.0328. Dropping ~40% of rows makes the model better at predicting everybody,
# so this is not specialisation.
#
# One confound the gate is immune to: each threshold early-stops on its own
# validation set, so the sweep varied the stopping rule as well as the training
# data (main used 203 / 143 / 138 trees at none / 1075 / 1100). Real games settle it.
#
# Baseline is build_v6 -- the artifact currently on the ladder as v054.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== export";  uv run python export_pure.py --tag v7m1075 2>&1 | tail -7
echo "=== parity";  uv run python parity_pure.py --tag v7m1075 --rows v7 --n 150 2>&1 | tail -4
echo "=== build + smoke"
uv run python build_submission.py --tag v7m1075 --n 25 2>&1 | tail -10

A=build_v7m1075/submission.tar.gz
echo "=== weighted field gate (baseline = build_v6 = v054)"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gq_alakazam.log 2>&1
printf "  alakazam   "; tail -1 gq_alakazam.log
uv run python eval_h2h.py --opp lucario --n 600 --artifact $A > gq_lucario.log 2>&1
printf "  lucario    "; tail -1 gq_lucario.log
for o in crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gq_$o.log 2>&1
  printf "  %-11s" $o; tail -1 gq_$o.log
done
echo "=== mirror cell: vs the shipped v6 build, n=600"
uv run python eval_h2h.py --n 600 --artifact $A \
    --opp gbdt:build_v6/submission.tar.gz > h2h_v7m1075_vs_v6.log 2>&1
tail -1 h2h_v7m1075_vs_v6.log
echo "=== V9 DONE"
