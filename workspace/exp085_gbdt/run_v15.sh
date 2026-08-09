#!/usr/bin/env bash
# v8 = the same 1,188,672-decision corpus with 24 opponent-side features appended
# (336 -> 360). Appended, so --n-feat 336 reproduces the v055 row exactly and the
# only difference between the two models below is the new features.
#
# What they encode, in deck terms:
#   threat   -- their Munkidori (マシマシラ) turns damage sitting on THEIR board
#               into damage on ours, so their real reach is attack damage plus up
#               to 30. We had own_movable_counters and no opposite number.
#   tracking -- in the mirror their 60 cards are ours, so unseen = our count minus
#               what is visible. Boss's Orders (ボスの指令) x2 is the card that
#               decides whether benching a second ex is safe.
#   prizes   -- an ex KO hands over 2 prizes (Mega ex 3). "How many KOs until
#               someone wins" is not len(prize); it depends on what is standing.
#
# The mirror is 42% of our ladder games and is the cell these target, so the
# mirror gate is the deciding one -- at n=1000, because n=400 reversed on us
# earlier today (0.560 vs 0.512 for the same build).
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== control: 336 features, >=1075 (must reproduce v7m1075's 0.8024)"
uv run python train_gbdt.py --rows v8 --min-score 1075 --rounds 900 --n-feat 336 \
    --out-tag v8c 2>&1 | grep -v "LightGBM\]" | tail -8
echo "=== candidate: 360 features, >=1075"
uv run python train_gbdt.py --rows v8 --min-score 1075 --rounds 900 \
    --out-tag v8 2>&1 | grep -v "LightGBM\]" | tail -8

echo "=== same held-out, control (336 cols)"
uv run python eval_fixed.py --rows v8 --tags v8c --n-feat 336 2>&1 | grep -v "LightGBM\]" | tail -8
echo "=== same held-out, candidate (360 cols)"
uv run python eval_fixed.py --rows v8 --tags v8 2>&1 | grep -v "LightGBM\]" | tail -8

echo "=== ship path"
uv run python export_pure.py --tag v8 2>&1 | tail -7
uv run python parity_pure.py --tag v8 --rows v8 --n 150 2>&1 | tail -4
uv run python build_submission.py --tag v8 --n 25 2>&1 | tail -10

A=build_v8/submission.tar.gz
echo "=== MIRROR gate vs the tetsutani reference, n=1000 (the deciding cell)"
uv run python eval_h2h.py --opp ref --n 1000 --artifact $A > mir_v8.log 2>&1
tail -1 mir_v8.log
echo "=== direct vs the shipped v054 build, n=800"
uv run python eval_h2h.py --n 800 --artifact $A \
    --opp gbdt:build_v6/submission.tar.gz > h2h_v8_vs_v6.log 2>&1
tail -1 h2h_v8_vs_v6.log
echo "=== field cells"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gt_alakazam.log 2>&1
printf "  alakazam   "; tail -1 gt_alakazam.log
for o in crustle dragapult archaludon lucario; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gt_$o.log 2>&1
  printf "  %-11s" $o; tail -1 gt_$o.log
done
echo "=== V15 DONE"
