#!/bin/bash
# Resumable chunked eval: 10 x 20-game chunks per matchup; skips finished chunks.
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1
mkdir -p chunks
run() { # $1=tag $2=MATCH $3=ONLY
  for c in $(seq 1 10); do
    mark="chunks/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=$2 ONLY=$3 uv run python eval_vg.py 20 2>&1 < /dev/null | tail -1 >> "vg_${1}.log" && touch "$mark"
  done
}
run v013 v013 ""
for m in ex_lucario mirror_chq crustle dragapult archaludon; do
  run "f_$m" field "$m"
done
touch ALL_DONE
