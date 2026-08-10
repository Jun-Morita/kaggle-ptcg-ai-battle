#!/usr/bin/env bash
# v10 corpus: 39 days (adds 08-09) and, for the first time, a teacher-strength
# CONDITIONING column instead of a teacher-strength FILTER. See feats.TEACHER_PCT.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
./scan_new_days.sh 2>&1 | tail -4
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v10 --index "$PWD/indices/*.json" > build_v10_rows.log 2>&1
echo "=== BUILD DONE"; tail -3 build_v10_rows.log
L="main=511,c7=255,mid=127,low=63,easy=31"
uv run python train_gbdt.py --rows v10 --rounds 900 --out-tag v10 --leaves "$L" --seed 0 \
    > train_v10.log 2>&1
grep -E "train_q|overall" train_v10.log
echo "=== V21 DONE"
