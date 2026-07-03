#!/bin/bash
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1 VG_MLP=value_mlp2.npz
mkdir -p chunks2
for c in $(seq 1 10); do
  [ -f "chunks2/cr_c${c}" ] && continue
  MATCH=field ONLY=crustle uv run python eval_vg.py 20 2>&1 < /dev/null | tail -1 >> vg2_crustle.log && touch "chunks2/cr_c${c}"
done
touch CRUSTLE2_DONE
