#!/usr/bin/env bash
# Ship gate for the two data-scaled builds. Both already beat the v054 build
# head-to-head at n=1600 (0.541 z+3.30 / 0.545 z+3.60), which is the first real
# win since v054 shipped. This is the weighted field gate that decides shipping
# (mirror-only gating is what produced the v046 mistake; see [[local-not-ladder]]).
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for T in v9a v9b; do
  A=build_$T/submission.tar.gz
  echo "=== weighted field gate: $T"
  uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > g_${T}_alakazam.log 2>&1
  printf "  alakazam   "; tail -1 g_${T}_alakazam.log
  uv run python eval_h2h.py --opp lucario --n 600 --artifact $A > g_${T}_lucario.log 2>&1
  printf "  lucario    "; tail -1 g_${T}_lucario.log
  for o in crustle dragapult archaludon; do
    uv run python eval_h2h.py --opp $o --n 200 --artifact $A > g_${T}_$o.log 2>&1
    printf "  %-11s" $o; tail -1 g_${T}_$o.log
  done
  echo "=== mirror vs the tetsutani reference, n=1000: $T"
  uv run python eval_h2h.py --opp ref --n 1000 --artifact $A > g_${T}_mirror.log 2>&1
  printf "  mirror     "; tail -1 g_${T}_mirror.log
done
echo "=== V20 DONE"
