#!/bin/bash
# exp042 -- v014(turnbeam) + BENCH_DISC=1 vs the 5-matchup field, n=200/matchup
# (10 resumable chunks of 20). Reuses exp035/eval_tb.py verbatim (same script
# that produced v014's n=200 baseline: crustle .905 / ex .77 / drag .17 /
# arch .195 / mirror .585, total 2.67), so results are directly comparable.
# MATCH=field only: no opponent in the field uses revenge_policy, so the
# process-wide BENCH_DISC env cannot contaminate the opponent side (paired
# candidate-vs-v014 needs separate builds and is a later step).
cd "$(dirname "$0")"
export REVENGE_BONUS=50 BENCH_DISC=1 PYTHONUNBUFFERED=1
mkdir -p chunks_bd
run() { # $1=matchup
  for c in $(seq 1 10); do
    mark="chunks_bd/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=field ONLY=$1 uv run python ../exp035_turnbeam/eval_tb.py 20 2>&1 < /dev/null | tail -1 >> "bd_${1}.log" && touch "$mark"
  done
}
for m in crustle mirror_chq ex_lucario dragapult archaludon; do
  run "$m"
done
touch BD_DONE
echo ALL_DONE
