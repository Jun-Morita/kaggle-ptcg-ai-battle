#!/usr/bin/env bash
# Gate the 2047-leaf variant. Held-out on all teachers puts it well ahead
# (0.8177 vs 0.8024 for 511), but held-out has now mis-ordered real play twice in
# this experiment -- v5, and L1023, which was ahead on held-out and lost the
# direct match 0.487. A 40-minute gate is cheaper than dismissing the largest
# offline signal we have on the strength of a pattern.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run python export_pure.py --tag q1075L2047 2>&1 | tail -7
uv run python parity_pure.py --tag q1075L2047 --rows v7 --n 150 2>&1 | tail -4
uv run python build_submission.py --tag q1075L2047 --n 25 2>&1 | tail -10
A=build_q1075L2047/submission.tar.gz
echo "=== weighted field gate"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gs_alakazam.log 2>&1
printf "  alakazam   "; tail -1 gs_alakazam.log
uv run python eval_h2h.py --opp lucario --n 600 --artifact $A > gs_lucario.log 2>&1
printf "  lucario    "; tail -1 gs_lucario.log
for o in crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gs_$o.log 2>&1
  printf "  %-11s" $o; tail -1 gs_$o.log
done
echo "=== vs the shipped v6 build (v054), n=600"
uv run python eval_h2h.py --n 600 --artifact $A \
    --opp gbdt:build_v6/submission.tar.gz > h2h_L2047_vs_v6.log 2>&1
tail -1 h2h_L2047_vs_v6.log
echo "=== vs the 511 leader, n=600"
uv run python eval_h2h.py --n 600 --artifact $A \
    --opp gbdt:build_v7m1075/submission.tar.gz > h2h_L2047_vs_L511.log 2>&1
tail -1 h2h_L2047_vs_L511.log
echo "=== V12 DONE"
