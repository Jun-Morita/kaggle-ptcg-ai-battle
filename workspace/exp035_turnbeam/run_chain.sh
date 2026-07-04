#!/bin/bash
# Resumable chunked eval for exp035 turn-beam
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1
mkdir -p chunks
run() { # $1=tag $2=MATCH $3=ONLY
  for c in $(seq 1 10); do
    mark="chunks/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=$2 ONLY=$3 uv run python eval_tb.py 20 2>&1 < /dev/null | tail -1 >> "tb_${1}.log" && touch "$mark"
  done
}
run v012 v012 ""
for m in ex_lucario dragapult mirror_chq crustle archaludon; do
  run "f_$m" field "$m"
done
touch ALL_DONE
