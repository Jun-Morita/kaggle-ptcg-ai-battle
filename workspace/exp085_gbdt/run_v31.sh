#!/usr/bin/env bash
# v12 on the corrected gate, at the same n as the v10rL/v056 comparison so the
# three are directly comparable. v056 = 0.6342, v10rL = 0.6640 (z +2.45).
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
A=build_v12/submission.tar.gz
uv run python eval_h2h.py --n 1200 --artifact $A \
    --opp gbdt:build_ex4b/submission.tar.gz > gg_v12_ex4.log 2>&1
printf "  mixed_ex4   "; tail -1 gg_v12_ex4.log
uv run python eval_h2h.py --opp ref --n 1200 --artifact $A > gg_v12_mirror.log 2>&1
printf "  mirror(ref) "; tail -1 gg_v12_mirror.log
uv run python eval_h2h.py --opp alakazam --n 800 --artifact $A > gg_v12_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_v12_alakazam.log
uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > gg_v12_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_v12_lucario.log
for o in crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gg_v12_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_v12_$o.log
done
echo "=== V31 DONE"
