#!/usr/bin/env bash
# Re-score the two rejected candidates on the field we ACTUALLY play.
#
# The old gate weighted Archaludon at 0.163 -- an archetype we did not meet once
# in 77 ladder games -- and had no cell at all for mixed_ex4, which is 16% of
# them and where the shipped build goes 0.463. Head-to-head against v056 is a
# mirror match and cannot see that: it says 0.511 for a build that is +0.069
# better where it counts.
#
# Weights below are the observed opponent mix from build v057's 77 games
# (results/meta_0811_55383659.json), not last month's guess.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for T in v11p00 v10rL; do
  A=build_$T/submission.tar.gz
  echo "=== $T"
  uv run python eval_h2h.py --opp ref --n 600 --artifact $A > g_${T}_mirror.log 2>&1
  printf "  mirror(ref) "; tail -1 g_${T}_mirror.log
  uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > g_${T}_alakazam.log 2>&1
  printf "  alakazam    "; tail -1 g_${T}_alakazam.log
  uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > g_${T}_lucario.log 2>&1
  printf "  lucario     "; tail -1 g_${T}_lucario.log
  for o in crustle dragapult; do
    uv run python eval_h2h.py --opp $o --n 200 --artifact $A > g_${T}_$o.log 2>&1
    printf "  %-11s " $o; tail -1 g_${T}_$o.log
  done
done
echo "=== V28 DONE"
