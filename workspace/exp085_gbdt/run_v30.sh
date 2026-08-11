#!/usr/bin/env bash
# The final candidate: the v10rL recipe rolled forward onto the two newest days.
#
# v10rL is the build the corrected gate puts ahead of the shipped v056 (0.6632
# vs 0.6509), and its recipe is: a 12-day window, our exact 60 cards, and the
# light tree budget (main 255) that costs nothing in strength and halves the
# time per move. Rolling the window from 07-28..08-08 to 07-30..08-10 keeps the
# length and adds the two days the ladder is finishing on.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "V29 DONE" run_v29.log 2>/dev/null; do sleep 60; done
./scan_new_days.sh 2>&1 | tail -3
mkdir -p idx_roll && rm -f idx_roll/*.json
for d in 2026-07-30 2026-07-31 2026-08-01 2026-08-02 2026-08-03 2026-08-04 \
         2026-08-05 2026-08-06 2026-08-07 2026-08-08 2026-08-09 2026-08-10; do
  [ -s "indices/$d.json" ] && ln -sf "../indices/$d.json" "idx_roll/$d.json"
done
echo "days: $(ls idx_roll | wc -l)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v12 --index "$PWD/idx_roll/*.json" > build_v12_rows.log 2>&1
grep -E "^target|^decisions" build_v12_rows.log
uv run python train_gbdt.py --rows v12 --rounds 900 --out-tag v12 --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_v12.log 2>&1
grep -E "train_q|overall" train_v12.log
uv run python export_pure.py --tag v12 2>&1 | tail -2
uv run python parity_pure.py --tag v12 --rows v12 --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v12 --n 25 2>&1 | tail -5
echo "=== V30 DONE"
