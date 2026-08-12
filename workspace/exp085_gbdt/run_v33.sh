#!/usr/bin/env bash
# v14: the v059 recipe with three more days on the end (07-28..08-11).
#
# Two reasons this is worth a slot rather than waiting. First, the next
# submission evicts the OLDER of the pair, which is v058 (870.3, flat) -- v059
# (910.1, still climbing) is not at risk. Second, the top of the ladder turned
# over between 08-11 and 08-12 (palsystem 1195 -> Sixth Sense 1233, and the
# whole top five changed), so 08-11's replays are the first that contain the
# field we will actually finish against.
#
# Extend, do not roll: v12 rolled the window forward, lost 19% of its decisions
# and scored 0.6418, while v13 extended it and scored 0.6584.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
./scan_new_days.sh 2>&1 | tail -3
mkdir -p idx_v14 && rm -f idx_v14/*.json
for d in 2026-07-28 2026-07-29 2026-07-30 2026-07-31 2026-08-01 2026-08-02 \
         2026-08-03 2026-08-04 2026-08-05 2026-08-06 2026-08-07 2026-08-08 \
         2026-08-09 2026-08-10 2026-08-11; do
  [ -s "indices/$d.json" ] && ln -sf "../indices/$d.json" "idx_v14/$d.json"
done
echo "days: $(ls idx_v14 | wc -l)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v14 --index "$PWD/idx_v14/*.json" > build_v14_rows.log 2>&1
grep -E "^target|^decisions" build_v14_rows.log
uv run python train_gbdt.py --rows v14 --rounds 900 --out-tag v14 --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_v14.log 2>&1
grep -E "train_q|overall" train_v14.log
uv run python export_pure.py --tag v14 2>&1 | tail -2
uv run python parity_pure.py --tag v14 --rows v14 --n 150 2>&1 | tail -2
uv run python build_submission.py --tag v14 --n 25 2>&1 | tail -5
A=build_v14/submission.tar.gz
echo "=== corrected gate (same n as v056/v10rL/v13)"
uv run python eval_h2h.py --n 1200 --artifact $A \
    --opp gbdt:build_ex4b/submission.tar.gz > gg_v14_ex4.log 2>&1
printf "  mixed_ex4   "; tail -1 gg_v14_ex4.log
uv run python eval_h2h.py --opp ref --n 1200 --artifact $A > gg_v14_mirror.log 2>&1
printf "  mirror(ref) "; tail -1 gg_v14_mirror.log
uv run python eval_h2h.py --opp alakazam --n 800 --artifact $A > gg_v14_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_v14_alakazam.log
uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > gg_v14_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_v14_lucario.log
for o in crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gg_v14_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_v14_$o.log
done
echo "=== V33 DONE"
