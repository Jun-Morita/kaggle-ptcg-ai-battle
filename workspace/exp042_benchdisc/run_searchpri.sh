#!/bin/bash
# exp043 -- v014(turnbeam) + SEARCH_PRI=1 vs the 5-matchup field, n=200/matchup
# (10 resumable chunks of 20). Same harness/reference as run_benchdisc.sh (v014
# baseline: crustle .905 / ex .77 / drag .17 / arch .195 / mirror .585, total 2.67).
cd "$(dirname "$0")"
export REVENGE_BONUS=50 SEARCH_PRI=1 PYTHONUNBUFFERED=1
mkdir -p chunks_sp
run() {
  for c in $(seq 1 10); do
    mark="chunks_sp/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=field ONLY=$1 uv run python ../exp035_turnbeam/eval_tb.py 20 2>&1 < /dev/null | tail -1 >> "sp_${1}.log" && touch "$mark"
  done
}
for m in crustle mirror_chq ex_lucario dragapult archaludon; do
  run "$m"
done
touch SP_DONE
echo ALL_DONE
