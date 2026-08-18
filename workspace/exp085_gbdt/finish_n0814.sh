#!/usr/bin/env bash
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
A="build_n0814/submission.tar.gz"
r() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }
r --opp lucario --n 400 --artifact "$A" > gg_n0814_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_n0814_lucario.log
for o in crustle dragapult; do
  r --opp $o --n 200 --artifact "$A" > "gg_n0814_$o.log" 2>&1
  printf "  %-11s " $o; tail -1 "gg_n0814_$o.log"
done
uv run python gate_score.py n0814
echo "=== N0814 GATE DONE"
