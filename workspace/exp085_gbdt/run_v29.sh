#!/usr/bin/env bash
# Resolve the three cells where v10rL and v056 disagree. Correcting the gate
# weights flipped the ordering (0.6632 vs 0.6509 where the old weights said
# 0.7518 vs 0.7528), but the propagated standard error is 0.0145 against a
# difference of 0.0123 -- z 0.85. Roughly tripling n on the cells that carry the
# difference is cheaper than another candidate, and it is the only thing that
# turns "the ordering changed" into "the ordering is real".
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for T in v10rL v9b; do
  A=build_$T/submission.tar.gz
  echo "=== $T"
  uv run python eval_h2h.py --n 1200 --artifact $A \
      --opp gbdt:build_ex4b/submission.tar.gz > gg_${T}_ex4.log 2>&1
  printf "  mixed_ex4   "; tail -1 gg_${T}_ex4.log
  uv run python eval_h2h.py --opp ref --n 1200 --artifact $A > gg_${T}_mirror.log 2>&1
  printf "  mirror(ref) "; tail -1 gg_${T}_mirror.log
  uv run python eval_h2h.py --opp alakazam --n 800 --artifact $A > gg_${T}_alakazam.log 2>&1
  printf "  alakazam    "; tail -1 gg_${T}_alakazam.log
done
echo "=== V29 DONE"
