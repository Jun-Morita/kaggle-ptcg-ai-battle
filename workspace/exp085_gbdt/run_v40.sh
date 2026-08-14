#!/usr/bin/env bash
# Name the opponent's cards.
#
# Every previous feature round added AGGREGATES of the other side -- bench count,
# total energy, best attack damage, a threat score. Three of them were rejected,
# the last at 0.500 with z 0.00 on n=1600. What none of them contained is the
# thing a player actually reads: which cards are on the table. Mist Energy on
# their active breaks the Munkidori (マシマシラ) damage-move plan; Air Balloon
# (ふうせん) means a gust traps nothing; Jamming Tower (ジャミングタワー) turns
# our Tools off. No count of energies expresses any of that.
#
# 40 cards x {on their board, in their discard} = 80 columns, 361 -> 441. The
# list is the union of the current archetypes' most common lists weighted by
# 08-12 share, minus our own 60 (already covered).
#
# Same 12-day window and seed as v059, so the featuriser is the only variable.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
run() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }

uv run python build_rows.py --arch mixed_ex3 --exact-deck --max-dec 3000000 \
    --out v16 --index "$PWD/idx_recent/*.json" > build_v16_rows.log 2>&1
grep -E "^target|^decisions|^skips" build_v16_rows.log
uv run python train_gbdt.py --rows v16 --rounds 900 --out-tag v16 --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_v16.log 2>&1
grep -E "train_q|overall" train_v16.log
uv run python export_pure.py --tag v16 2>&1 | tail -2
uv run python parity_pure.py --tag v16 --rows v16 --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v16 --n 25 2>&1 | tail -5
A=build_v16/submission.tar.gz
echo "=== frozen gate (bar: v059 = 0.6640)"
run --n 1200 --artifact $A --opp gbdt:build_ex4b/submission.tar.gz > gg_v16_ex4.log 2>&1
printf "  mixed_ex4   "; tail -1 gg_v16_ex4.log
run --opp ref --n 1200 --artifact $A > gg_v16_mirror.log 2>&1
printf "  mirror(ref) "; tail -1 gg_v16_mirror.log
run --n 1200 --artifact $A --opp gbdt:build_ebd/submission.tar.gz > gg_v16_ebd.log 2>&1
printf "  ex_beatdown "; tail -1 gg_v16_ebd.log
run --opp alakazam --n 800 --artifact $A > gg_v16_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_v16_alakazam.log
run --opp lucario --n 400 --artifact $A > gg_v16_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_v16_lucario.log
for o in crustle dragapult; do
  run --opp $o --n 200 --artifact $A > gg_v16_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_v16_$o.log
done
uv run python gate_score.py v16
echo "=== V40 DONE"
