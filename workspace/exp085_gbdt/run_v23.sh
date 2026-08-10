#!/usr/bin/env bash
# Recency vs volume. Yesterday's +76%-data win cannot separate the two: every
# added day was a recent one. This holds the featuriser and the conditioning
# fixed and cuts the corpus to the last 14 days -- 40% of the rows, all from
# after the meta rotated (mixed_ex3 71.5% on 07-31 -> 25.6% on 08-08).
#
# The days cannot be sliced out of rows_v10.pkl: build_rows interleaves seats
# across days (zip_longest), so a qid range is a mix of dates, not a window.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p idx_recent && rm -f idx_recent/*.json
for d in 2026-07-28 2026-07-29 2026-07-30 2026-07-31 2026-08-01 2026-08-02 \
         2026-08-03 2026-08-04 2026-08-05 2026-08-06 2026-08-07 2026-08-08; do
  [ -s "indices/$d.json" ] && ln -sf "../indices/$d.json" "idx_recent/$d.json"
done
ls idx_recent | wc -l
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v10r --index "$PWD/idx_recent/*.json" > build_v10r_rows.log 2>&1
echo "=== BUILD DONE"; grep -E "^target|^decisions" build_v10r_rows.log
L="main=511,c7=255,mid=127,low=63,easy=31"
uv run python train_gbdt.py --rows v10r --rounds 900 --out-tag v10r --leaves "$L" --seed 0 \
    > train_v10r.log 2>&1
grep -E "train_q|overall" train_v10r.log
uv run python export_pure.py --tag v10r 2>&1 | tail -2
uv run python parity_pure.py --tag v10r --rows v10r --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v10r --n 25 2>&1 | tail -5
echo "=== recent-only vs the full 39-day build, n=1600"
uv run python eval_h2h.py --n 1600 --artifact build_v10r/submission.tar.gz \
    --opp gbdt:build_v10/submission.tar.gz > h2h_v10r_vs_v10.log 2>&1
tail -1 h2h_v10r_vs_v10.log
echo "=== V23 DONE"
