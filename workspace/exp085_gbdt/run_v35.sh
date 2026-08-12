#!/usr/bin/env bash
# The strongest mixed_ex4 pilot we can build, so the deck question is answered
# by the deck and not by a thin corpus.
#
# ex4b already covered every day, so "train on the newest data" cannot add
# seats -- the newest days ARE most of its corpus (mixed_ex4 barely existed
# before 08-01). The only untapped data is the 24% of mixed_ex4 teachers whose
# list is not exactly the top one, so this relaxes the deck filter to 58/60,
# the same threshold that kept 88.6% of our own archetype.
#
# Prior expectation, stated before the run: ex4b lost by 0.092 on the weighted
# gate, with the damage in alakazam (-0.205), lucario (-0.257) and dragapult
# (-0.330). A third more data will not close that; those look like matchup
# properties of the deck. Worth measuring rather than asserting.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PTCG_DECK_JSON="$PWD/deck_mixed_ex4.json"
uv run python build_rows.py --arch mixed_ex4 --exact-deck --near 58 \
    --deck deck_mixed_ex4.json --max-dec 3000000 --out ex4c \
    --index "$PWD/indices/*.json" > build_ex4c.log 2>&1
grep -E "^target|near-deck|^decisions|^skips" build_ex4c.log
uv run python train_gbdt.py --rows ex4c --rounds 900 --out-tag ex4c --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_ex4c.log 2>&1
grep -E "train_q|overall" train_ex4c.log
uv run python export_pure.py --tag ex4c 2>&1 | tail -2
uv run python parity_pure.py --tag ex4c --rows ex4c --n 150 2>&1 | tail -2
uv run python build_submission.py --tag ex4c --n 25 --deck deck_mixed_ex4.json 2>&1 | tail -5
A=build_ex4c/submission.tar.gz
echo "=== gate: the 42% cell is vs OUR shipped v059"
uv run python eval_h2h.py --n 1200 --artifact $A \
    --opp gbdt:build_v10rL/submission.tar.gz > gg_ex4c_vs_v059.log 2>&1
printf "  vs v059     "; tail -1 gg_ex4c_vs_v059.log
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gg_ex4c_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_ex4c_alakazam.log
uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > gg_ex4c_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_ex4c_lucario.log
for o in crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gg_ex4c_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_ex4c_$o.log
done
echo "=== V35 DONE"
