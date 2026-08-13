#!/usr/bin/env bash
# Candidates on OTHER DECKS, scored on the same seven opponents.
#
# The reason to look: teacher strength splits hard by archetype. Taking each
# day's teachers and ranking them inside that day's whole field, the medians for
# August run
#     ex_beatdown 68-86%   dragapult 44-88%   mixed_ex4 31-59%
#     mixed_ex3 (ours) 31-51%   mixed_ex1 14-54%
# so our deck is mostly piloted by below-average players, and ex_beatdown by the
# strongest cohort on the ladder. mixed_ex4 was already tried and failed (0.5931
# vs v059's 0.6640) -- it beats US but loses to the field. ex_beatdown is a
# different claim: not a matchup, a level.
#
# Runs after v36, which builds the ex_beatdown model and measures our builds
# against it; this adds the cells needed to score it as a CANDIDATE, then does
# the same for dragapult.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "V36 DONE" run_v36.log 2>/dev/null; do sleep 120; done
run() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }

cells_for() {   # $1 = tag whose artifact we score
  local T=$1 A=build_$1/submission.tar.gz
  run --n 1200 --artifact $A --opp gbdt:build_v10rL/submission.tar.gz > xd_${T}_ex3.log 2>&1
  printf "  %-5s vs ex3(v059)  " $T; tail -1 xd_${T}_ex3.log
  run --n 1200 --artifact $A --opp gbdt:build_ex4b/submission.tar.gz > xd_${T}_ex4.log 2>&1
  printf "  %-5s vs ex4        " $T; tail -1 xd_${T}_ex4.log
  run --n 800 --artifact $A --opp alakazam > xd_${T}_ex1.log 2>&1
  printf "  %-5s vs alakazam   " $T; tail -1 xd_${T}_ex1.log
  run --n 400 --artifact $A --opp dragapult > xd_${T}_dragapult.log 2>&1
  printf "  %-5s vs dragapult  " $T; tail -1 xd_${T}_dragapult.log
  run --n 400 --artifact $A --opp lucario > xd_${T}_lucario.log 2>&1
  printf "  %-5s vs lucario    " $T; tail -1 xd_${T}_lucario.log
  run --n 200 --artifact $A --opp crustle > xd_${T}_crustle.log 2>&1
  printf "  %-5s vs crustle    " $T; tail -1 xd_${T}_crustle.log
}

echo "=== A. ex_beatdown as a CANDIDATE"
cells_for ebd
uv run python cross_deck.py v10rL ebd ex4c

echo "=== B. build a dragapult agent"
uv run python probe_arch.py --arch dragapult --days 08-08,08-09,08-10,08-11,08-12 \
    --cap 500 2>&1 | tail -8
export PTCG_DECK_JSON="$PWD/deck_dragapult.json"
uv run python build_rows.py --arch dragapult --exact-deck --near 58 \
    --deck deck_dragapult.json --max-dec 3000000 --out drg \
    --index "$PWD/indices/*.json" > build_drg.log 2>&1
grep -E "^target|near-deck|^decisions" build_drg.log
uv run python train_gbdt.py --rows drg --rounds 900 --out-tag drg --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_drg.log 2>&1
grep -E "train_q|overall" train_drg.log
uv run python export_pure.py --tag drg 2>&1 | tail -2
uv run python parity_pure.py --tag drg --rows drg --n 150 2>&1 | tail -2
uv run python build_submission.py --tag drg --n 25 --deck deck_dragapult.json 2>&1 | tail -5
unset PTCG_DECK_JSON
echo "=== C. dragapult as a CANDIDATE"
cells_for drg
run --n 1200 --artifact build_drg/submission.tar.gz \
    --opp gbdt:build_ebd/submission.tar.gz > xd_drg_ebd.log 2>&1
printf "  drg   vs ex_beatdown "; tail -1 xd_drg_ebd.log
uv run python cross_deck.py v10rL ebd drg ex4c
echo "=== V37 DONE"
