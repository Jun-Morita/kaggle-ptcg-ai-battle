#!/usr/bin/env bash
# Re-test the clone decks now that the field has moved and the data has grown.
#
# The five deck clones were all built and rejected on 08-13/08-14, off corpora
# that stopped at 08-12. Two things have changed since:
#
#   1. Volume. dragapult went 5,763 -> 8,354 seats (+45%), and 4,655 of those are
#      08-08 or later. ex_beatdown 6,927 (4,012 recent); mixed_ex4 6,330 (3,278).
#      The earlier ex_beatdown build had 49,418 decisions, which was never a fair
#      test of anything.
#   2. Who is playing them. On 08-15 dragapult is 34.2% of the field and
#      ex_beatdown 27.3% -- 61.5% between them -- while our mixed_ex3 has fallen
#      to 6.1% from 25.6% a week ago. The final weekend's teachers are the
#      strongest submissions of the competition, and they are playing these decks.
#
# Each deck gets its top-1 list re-extracted from the LAST FOUR DAYS, because the
# list that was most common on 08-08 is not necessarily the one being played now.
#
# Read-out is main top-k, i.e. fidelity, not strength. Comparing across decks at
# equal volume is the meaningful axis (our deck sits at 0.7098). Anything that
# closes most of that gap earns a gate run; nothing here ships on top-k alone.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# reference points from the 08-13/08-14 builds, for the summary at the end
declare -A PREV=( [dragapult]="0.5841 @250,529" [ex_beatdown]="0.6086 @49,418"
                  [mixed_ex4]="0.6075 @245,279" )

for ARCH in dragapult ex_beatdown mixed_ex4; do
  TAG="${ARCH:0:3}2"
  echo "=== $ARCH -> $TAG   (was ${PREV[$ARCH]})"
  uv run python probe_arch.py --arch "$ARCH" --days 08-12,08-13,08-14,08-15 \
      --cap 600 2>&1 | grep -E "seats sampled|seats \(|wrote" | head -6

  DECK="$PWD/deck_$ARCH.json"
  export PTCG_DECK_JSON="$DECK"      # train_gbdt imports feats for IDX/CATEGORICAL
  uv run python build_rows.py --arch "$ARCH" --deck "$DECK" --exact-deck --near 58 \
      --max-dec 1500000 --out "$TAG" --index "$PWD/indices/2026-*.json" \
      > "build_${TAG}.log" 2>&1
  grep -E "^target|^  exact-deck|^decisions|^skips" "build_${TAG}.log"

  uv run python train_gbdt.py --rows "$TAG" --rounds 900 --out-tag "$TAG" --seed 0 \
      --leaves main=255,c7=127,mid=127,low=63,easy=31 > "train_${TAG}.log" 2>&1
  grep -E "^  main |overall" "train_${TAG}.log"
  unset PTCG_DECK_JSON
done
echo "=== DECKS2 DONE"
