#!/bin/bash
# v014 candidate = guard(K=4 doom veto) over turnbeam base. Resumable chunks.
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1 GUARD_BASE=turnbeam
mkdir -p chunks14
run() { # $1=tag $2=MATCH $3=ONLY
  for c in $(seq 1 10); do
    mark="chunks14/${1}_c${c}"
    [ -f "$mark" ] && continue
    MATCH=$2 ONLY=$3 uv run python eval_guard.py 20 2>&1 < /dev/null | tail -1 >> "v14_${1}.log" && touch "$mark"
  done
}
for m in ex_lucario crustle dragapult mirror_chq archaludon; do
  run "f_$m" field "$m"
done
run v012 paired ""
touch V14_DONE
