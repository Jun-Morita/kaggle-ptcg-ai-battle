#!/usr/bin/env bash
# v13: extend the window rather than roll it.
#
# v12 rolled 07-28..08-08 forward to 07-30..08-10 and came out 0.0222 below
# v10rL. It did not lose because the new days are bad -- it lost 19% of its
# decisions, because the two days it dropped (07-28: 2,725 seats, 07-29: 1,513)
# are far larger than the two it gained (08-09: 757, 08-10: 554). Volume is the
# one lever that has ever measured, so keep every day v10rL had and add the new
# ones on top.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p idx_ext && rm -f idx_ext/*.json
for d in 2026-07-28 2026-07-29 2026-07-30 2026-07-31 2026-08-01 2026-08-02 \
         2026-08-03 2026-08-04 2026-08-05 2026-08-06 2026-08-07 2026-08-08 \
         2026-08-09 2026-08-10; do
  [ -s "indices/$d.json" ] && ln -sf "../indices/$d.json" "idx_ext/$d.json"
done
echo "days: $(ls idx_ext | wc -l)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v13 --index "$PWD/idx_ext/*.json" > build_v13_rows.log 2>&1
grep -E "^target|^decisions" build_v13_rows.log
uv run python train_gbdt.py --rows v13 --rounds 900 --out-tag v13 --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_v13.log 2>&1
grep -E "train_q|overall" train_v13.log
uv run python export_pure.py --tag v13 2>&1 | tail -2
uv run python parity_pure.py --tag v13 --rows v13 --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v13 --n 25 2>&1 | tail -5
A=build_v13/submission.tar.gz
echo "=== corrected gate, same n as v056/v10rL/v12"
uv run python eval_h2h.py --n 1200 --artifact $A \
    --opp gbdt:build_ex4b/submission.tar.gz > gg_v13_ex4.log 2>&1
printf "  mixed_ex4   "; tail -1 gg_v13_ex4.log
uv run python eval_h2h.py --opp ref --n 1200 --artifact $A > gg_v13_mirror.log 2>&1
printf "  mirror(ref) "; tail -1 gg_v13_mirror.log
uv run python eval_h2h.py --opp alakazam --n 800 --artifact $A > gg_v13_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_v13_alakazam.log
uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > gg_v13_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_v13_lucario.log
for o in crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gg_v13_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_v13_$o.log
done
echo "=== V32 DONE"
