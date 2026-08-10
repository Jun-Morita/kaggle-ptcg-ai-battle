#!/usr/bin/env bash
# Does teacher-strength CONDITIONING beat the shipped v056? The corpus differs
# from v9 by two things: 07-29 was added (a day whose download had been empty),
# and every row now carries feats.TEACHER_PCT -- the author's rank within their
# own day -- which the agent pins to 1.0 at inference.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T=v10
uv run python export_pure.py --tag $T 2>&1 | tail -3
uv run python parity_pure.py --tag $T --rows v10 --n 150 2>&1 | tail -3
uv run python build_submission.py --tag $T --n 25 2>&1 | tail -6
A=build_$T/submission.tar.gz
echo "=== $T vs the SHIPPED v056 build, n=1600"
uv run python eval_h2h.py --n 1600 --artifact $A \
    --opp gbdt:build_v9b/submission.tar.gz > h2h_${T}_vs_v9b.log 2>&1
tail -1 h2h_${T}_vs_v9b.log
echo "=== weighted field gate"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > g_${T}_alakazam.log 2>&1
printf "  alakazam   "; tail -1 g_${T}_alakazam.log
uv run python eval_h2h.py --opp lucario --n 600 --artifact $A > g_${T}_lucario.log 2>&1
printf "  lucario    "; tail -1 g_${T}_lucario.log
for o in crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > g_${T}_$o.log 2>&1
  printf "  %-11s" $o; tail -1 g_${T}_$o.log
done
echo "=== V22 DONE"
