#!/bin/bash
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1 TB_K=3 TB_BEAM=10 TB_BRANCH=16 TB_MAXSTEPS=3000
mkdir -p chunks_wide
run() { # $1=tag $2=ONLY
  for c in $(seq 1 10); do
    mark="chunks_wide/${1}_c${c}"
    [ -f "$mark" ] && continue
    ONLY=$2 uv run python eval_config.py 20 wide 2>&1 < /dev/null | tail -1 >> "wide_${1}.log" && touch "$mark"
  done
}
for m in ex_lucario dragapult archaludon mirror_chq crustle; do
  run "$m" "$m"
done
touch WIDE_DONE
