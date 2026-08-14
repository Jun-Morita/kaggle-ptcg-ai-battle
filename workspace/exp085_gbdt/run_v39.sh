#!/usr/bin/env bash
# Match the training distribution to the field, instead of adding to it.
#
# Every corpus we have is dominated by the meta of late July, when 63% of the
# ladder played our own deck. On 08-12 the field was dragapult 25.8% /
# ex_beatdown 20.6% / mixed_ex4 15.8% / mixed_ex3 14.1%. So the model is fluent
# in a mirror match that has largely stopped happening.
#
# build_rows already computed the opponent's archetype for every row and threw
# it away. It now rides in the corpus, and --opp-mix turns it into LightGBM row
# weights that bend the mix toward the 08-12 field. Nothing is discarded -- a
# game against a deck nobody plays any more just counts for less.
#
# Single variable: same 12-day window as v059 (the best build we have), same
# seed, same leaves. The no-mix arm should reproduce v059 and is the control
# that proves the rebuild changed nothing else.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "V38 DONE" run_v38.log 2>/dev/null; do sleep 120; done
run() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }

echo "=== corpus 07-28..08-08 WITH the opponent column"
uv run python build_rows.py --arch mixed_ex3 --exact-deck --max-dec 3000000 \
    --out v15 --index "$PWD/idx_recent/*.json" > build_v15_rows.log 2>&1
grep -E "^target|^decisions" build_v15_rows.log
uv run python - <<'PY'
import pickle, collections, os
import numpy as np
p = os.path.join("results", "rows_v15.pkl")
c = collections.Counter()
with open(p, "rb") as f:
    while True:
        try:
            t = pickle.load(f)
        except EOFError:
            break
        for k, v in zip(*np.unique(t[5], return_counts=True)):
            c[int(k)] += int(v)
tot = sum(c.values())
NAME = {1: "mixed_ex3", 2: "mixed_ex1", 3: "mixed_ex4", 4: "dragapult",
        5: "ex_beatdown", 6: "crustle", 7: "lucario", 8: "non_ex", 9: "mixed_ex2", 0: "other"}
TGT = {1: .141, 2: .114, 3: .158, 4: .258, 5: .206, 6: .053, 7: .066}
print("  opponent mix in the corpus vs the 08-12 field:")
for k, v in c.most_common():
    print(f"    {NAME.get(k,k):<12}{v/tot:>7.1%}   target {TGT.get(k,0):>6.1%}")
PY

L="main=255,c7=127,mid=127,low=63,easy=31"
for ARM in plain mix; do
  T="v15$ARM"
  EXTRA=""; [ "$ARM" = mix ] && EXTRA="--opp-mix"
  echo "=== train $T $EXTRA"
  uv run python train_gbdt.py --rows v15 --rounds 900 --out-tag $T --seed 0 \
      --leaves "$L" $EXTRA > train_$T.log 2>&1
  grep -E "train_q|overall" train_$T.log
  uv run python export_pure.py --tag $T 2>&1 | tail -2
  uv run python parity_pure.py --tag $T --rows v15 --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag $T --n 25 2>&1 | tail -5
  A=build_$T/submission.tar.gz
  echo "  --- frozen gate"
  run --n 1200 --artifact $A --opp gbdt:build_ex4b/submission.tar.gz > gg_${T}_ex4.log 2>&1
  printf "    mixed_ex4   "; tail -1 gg_${T}_ex4.log
  run --opp ref --n 1200 --artifact $A > gg_${T}_mirror.log 2>&1
  printf "    mirror(ref) "; tail -1 gg_${T}_mirror.log
  run --n 1200 --artifact $A --opp gbdt:build_ebd/submission.tar.gz > gg_${T}_ebd.log 2>&1
  printf "    ex_beatdown "; tail -1 gg_${T}_ebd.log
  run --opp alakazam --n 800 --artifact $A > gg_${T}_alakazam.log 2>&1
  printf "    alakazam    "; tail -1 gg_${T}_alakazam.log
  run --opp lucario --n 400 --artifact $A > gg_${T}_lucario.log 2>&1
  printf "    lucario     "; tail -1 gg_${T}_lucario.log
  for o in crustle dragapult; do
    run --opp $o --n 200 --artifact $A > gg_${T}_$o.log 2>&1
    printf "    %-11s " $o; tail -1 gg_${T}_$o.log
  done
  uv run python gate_score.py $T
done
echo "=== V39 DONE"
