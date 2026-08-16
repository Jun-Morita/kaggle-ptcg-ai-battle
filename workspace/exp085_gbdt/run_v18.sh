#!/usr/bin/env bash
# Do the nine PTCG-theory aggregates buy anything? Measured on dragapult.
#
# Why not on our own deck: main top-k there is 0.7098 / 0.7054 / 0.7098 at
# 236k / 458k / 1,400k decisions -- flat under a 6x change in data. It is
# saturated, which is also why five feature additions in a row measured as
# nothing. dragapult sits at 0.5841 on 250k decisions, a 0.126 gap at the same
# volume, so the headroom is there and it is a representation gap by elimination.
#
# And dragapult is the archetype the features are FOR. ptcg_strategy.md files it
# under Spread: put counters across the bench, then collect several small
# Pokemon at once. Four of the nine columns count exactly that.
#
# Paired: same deck, same days, same seed, same leaves. Only PTCG_V18 differs.
# The read-out is main top-k, which is a fidelity number, NOT strength -- across
# DATA VOLUME it has been anti-correlated with the gate five times. Here the data
# is fixed and only the columns move, so it should be the cleaner direction, but
# anything that survives here still has to clear the gate.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# --deck, NOT PTCG_DECK_JSON. build_rows resolves --exact-deck against --deck and
# then calls feats.set_deck() with it, which overwrites whatever the env var had
# loaded. The first attempt exported only PTCG_DECK_JSON, so dragapult teachers
# were matched against OUR Grimmsnarl list: 5,227 seats in, 0 rows out, three and
# a half hours of CPU. Same shape as the v060 bug where deck.csv never reached
# the featuriser.
# BOTH are needed, which is the part the first attempt got wrong:
#   --deck            build_rows' exact/near filter, and the set_deck it then does
#   PTCG_DECK_JSON    train_gbdt imports feats directly for IDX / CATEGORICAL,
#                     and would otherwise index a dragapult corpus with Grimmsnarl
#                     column names
DECK="$PWD/deck_dragapult.json"
export PTCG_DECK_JSON="$DECK"

for MODE in off on; do
  TAG="drg18$MODE"
  if [ "$MODE" = on ]; then export PTCG_V18=1; else unset PTCG_V18 || true; fi
  echo "=== $TAG  (PTCG_V18=${PTCG_V18:-unset})"
  # --near 58: dragapult lists split 21 ways, so exact-60 matching keeps only a
  # fraction of the seats. 58/60 overlap is what the working cross-deck build used.
  # --max-dec 800000: 3,000,000 built a corpus large enough that running it beside
  # the n0814 gate ran the box out of memory and killed the gate. A paired
  # comparison does not need more than this.
  uv run python build_rows.py --arch dragapult --deck "$DECK" --exact-deck --near 58 \
      --max-dec 800000 \
      --out "$TAG" --index "$PWD/indices/2026-08-*.json" > "build_${TAG}.log" 2>&1
  grep -E "^target|^  exact-deck|^decisions" "build_${TAG}.log"
  uv run python train_gbdt.py --rows "$TAG" --rounds 900 --out-tag "$TAG" --seed 0 \
      --leaves main=255,c7=127,mid=127,low=63,easy=31 > "train_${TAG}.log" 2>&1
  grep -E "^  main |overall" "train_${TAG}.log"
done
echo "=== V18 DONE"
