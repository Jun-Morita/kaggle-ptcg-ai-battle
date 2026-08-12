#!/usr/bin/env bash
# Is the DECK the difference? ex4b was rejected as our agent on 08-09 (top-k
# 0.586 against our 0.71, a quarter of the teacher data) and it still goes
# 0.541 / 0.507 / 0.493 against v056 / v058 / v059. If a weak pilot on Mega
# Lopunny ex matches a well-trained one on Grimmsnarl, the deck is carrying it.
#
# Scored on the SAME observed field mix, with the 42% cell being mixed_ex3 (its
# opponent, i.e. our own build) and the 16% cell being its own mirror, which is
# 0.500 by construction. Everything else is measured here.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "V33 DONE" run_v33.log 2>/dev/null; do sleep 60; done
A=build_ex4b/submission.tar.gz
uv run python eval_h2h.py --opp alakazam --n 400 --artifact $A > gg_ex4b_alakazam.log 2>&1
printf "  alakazam    "; tail -1 gg_ex4b_alakazam.log
uv run python eval_h2h.py --opp lucario --n 400 --artifact $A > gg_ex4b_lucario.log 2>&1
printf "  lucario     "; tail -1 gg_ex4b_lucario.log
for o in crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $A > gg_ex4b_$o.log 2>&1
  printf "  %-11s " $o; tail -1 gg_ex4b_$o.log
done
echo "=== V34 DONE"
