#!/bin/bash
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1
mkdir -p chunks_b2
run() { # $1=tag $2=MATCH $3=ONLY
  for c in $(seq 1 2); do
    mark="chunks_b2/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=$2 ONLY=$3 uv run python eval_b2.py 20 2>&1 < /dev/null | tail -1 >> "b2_${1}.log" && touch "$mark"
  done
}
for m in ex_lucario dragapult archaludon mirror_chq crustle; do
  run "f_$m" field "$m"
done
touch B2_DONE
