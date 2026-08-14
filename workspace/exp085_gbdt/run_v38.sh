#!/usr/bin/env bash
# The remaining clonable archetypes, measured the same way as everything else.
#
# Clonability, from five days of replays: lucario_ex 92% on one list, mixed_ex1
# 69%, mixed_ex3 (ours) 69%, mixed_ex4 72%. Those four are the whole set --
# dragapult is 36% and ex_beatdown 19%, and the ex_beatdown clone proved the
# point by losing every cell (0.159 to 0.269) on 840 usable seats.
#
# Neither of these is an obvious win: mixed_ex1's teachers are the weakest cohort
# on the ladder (median 14-54% of the field, against our 31-51%) and we already
# beat it 0.880, while lucario_ex is only 6.6% of the field and we beat it 0.652.
# But the point of a sweep is not to confirm a hunch -- rejecting mixed_ex4 and
# ex_beatdown by measurement is what makes "stay on Grimmsnarl" a finding rather
# than an assumption.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "V37 DONE" run_v37.log 2>/dev/null; do sleep 120; done
run() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }

for SPEC in "lucario_ex:luc" "mixed_ex1:ak"; do
  ARCH=${SPEC%%:*}; T=${SPEC##*:}
  echo "=== $ARCH -> $T"
  uv run python probe_arch.py --arch $ARCH --days 08-08,08-09,08-10,08-11,08-12 \
      --cap 500 2>&1 | grep -E "seats sampled|top lists|seats \(|wrote" | head -8
  export PTCG_DECK_JSON="$PWD/deck_$ARCH.json"
  uv run python build_rows.py --arch $ARCH --exact-deck --near 58 \
      --deck deck_$ARCH.json --max-dec 3000000 --out $T \
      --index "$PWD/indices/*.json" > build_$T.log 2>&1
  grep -E "^target|^decisions|^skips" build_$T.log
  uv run python train_gbdt.py --rows $T --rounds 900 --out-tag $T --seed 0 \
      --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_$T.log 2>&1
  grep -E "train_q|overall" train_$T.log
  uv run python export_pure.py --tag $T 2>&1 | tail -2
  uv run python parity_pure.py --tag $T --rows $T --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag $T --n 25 --deck deck_$ARCH.json 2>&1 | tail -5
  unset PTCG_DECK_JSON
  A=build_$T/submission.tar.gz
  run --n 1200 --artifact $A --opp gbdt:build_v10rL/submission.tar.gz > xd_${T}_ex3.log 2>&1
  printf "  %-4s vs ex3(v059)  " $T; tail -1 xd_${T}_ex3.log
  run --n 1200 --artifact $A --opp gbdt:build_ex4b/submission.tar.gz > xd_${T}_ex4.log 2>&1
  printf "  %-4s vs ex4        " $T; tail -1 xd_${T}_ex4.log
  run --n 1200 --artifact $A --opp gbdt:build_ebd/submission.tar.gz > xd_${T}_ebd.log 2>&1
  printf "  %-4s vs ex_beatdown" $T; tail -1 xd_${T}_ebd.log
  run --n 800 --artifact $A --opp alakazam > xd_${T}_ex1.log 2>&1
  printf "  %-4s vs alakazam   " $T; tail -1 xd_${T}_ex1.log
  run --n 400 --artifact $A --opp dragapult > xd_${T}_dragapult.log 2>&1
  printf "  %-4s vs dragapult  " $T; tail -1 xd_${T}_dragapult.log
  run --n 400 --artifact $A --opp lucario > xd_${T}_lucario.log 2>&1
  printf "  %-4s vs lucario    " $T; tail -1 xd_${T}_lucario.log
  run --n 200 --artifact $A --opp crustle > xd_${T}_crustle.log 2>&1
  printf "  %-4s vs crustle    " $T; tail -1 xd_${T}_crustle.log
done
uv run python cross_deck.py v10rL drg luc ak ex4c ebd
echo "=== V38 DONE"
