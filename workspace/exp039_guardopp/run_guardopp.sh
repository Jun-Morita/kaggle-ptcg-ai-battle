#!/bin/bash
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1
mkdir -p chunks_go
run() { # $1=tag $2=MATCH $3=ONLY
  for c in $(seq 1 5); do
    mark="chunks_go/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=$2 ONLY=$3 uv run python eval_guardopp.py 20 2>&1 < /dev/null | tail -1 >> "go_${1}.log" && touch "$mark"
  done
}
for m in ex_lucario dragapult archaludon mirror_chq crustle; do
  run "f_$m" field "$m"
done
run v012 v012 ""
run v014 v014 ""
touch GO_DONE
