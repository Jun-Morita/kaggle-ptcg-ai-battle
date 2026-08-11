#!/usr/bin/env bash
# Track B: only teachers who did well IN THE NEW META.
#
# Three conditions at once, each one chosen because the alternative has already
# been measured and rejected:
#   window  13 days (07-29..08-09). The 39-day corpus is not better (0.511).
#   deck    overlap >= 58/60 instead of exact. 74% of recent mixed_ex3 teachers
#           already run our exact list and 13% miss by two cards (they cut Tool
#           Scrapper / Pokegear 3.0 for Handheld Fan / Judge); below that there
#           is a cliff straight to 18/60, which is a different deck.
#   strength applied at TRAIN time on the per-day percentile already stored in
#           the corpus, so several thresholds cost one build instead of three.
#
# The absolute >=1075 filter failed (0.545 vs 0.541) and conditioning failed
# (0.511, z +0.90). Neither was ever tried INSIDE a recent-only window, where
# "did well" means "did well against the current field" rather than "played in
# July, when scores ran higher".
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p idx_recent2 && rm -f idx_recent2/*.json
for d in 2026-07-29 2026-07-30 2026-07-31 2026-08-01 2026-08-02 2026-08-03 \
         2026-08-04 2026-08-05 2026-08-06 2026-08-07 2026-08-08 2026-08-09; do
  [ -s "indices/$d.json" ] && ln -sf "../indices/$d.json" "idx_recent2/$d.json"
done
echo "days: $(ls idx_recent2 | wc -l)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck --near 58 \
    --max-dec 3000000 --out v11 --index "$PWD/idx_recent2/*.json" > build_v11_rows.log 2>&1
echo "=== BUILD DONE"; grep -E "^target|near-deck|^decisions|^skips" build_v11_rows.log
L="main=255,c7=127,mid=127,low=63,easy=31"
for M in 0.0 0.5; do
  TAG="v11p${M/./}"
  echo "=== train $TAG (percentile >= $M)"
  uv run python train_gbdt.py --rows v11 --rounds 900 --out-tag $TAG --leaves "$L" \
      --seed 0 --min-score $M > train_$TAG.log 2>&1
  grep -E "train_q|overall" train_$TAG.log
  uv run python export_pure.py --tag $TAG 2>&1 | tail -2
  uv run python parity_pure.py --tag $TAG --rows v11 --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag $TAG --n 25 2>&1 | tail -5
  echo "=== $TAG vs v056, n=1600"
  uv run python eval_h2h.py --n 1600 --artifact build_$TAG/submission.tar.gz \
      --opp gbdt:build_v9b/submission.tar.gz > h2h_${TAG}_vs_v9b.log 2>&1
  tail -1 h2h_${TAG}_vs_v9b.log
done
echo "=== V25 DONE"
