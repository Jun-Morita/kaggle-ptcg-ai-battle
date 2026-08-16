#!/usr/bin/env bash
# Extend the x4b3 result to the two decks that actually own the field.
#
# x4b3 lifted mixed_ex4 rows 3x -- 5.5% of the corpus -- and moved the gate from
# 0.6604 to 0.6806, the first pass over the v059 bar in eight attempts, with five
# of six cells at their best ever. The intervention was tiny and the untouched
# cells improved too.
#
# The same argument is stronger for the other two. Real ladder win rates for our
# exact 60 cards over the last three days, against what the corpus actually holds:
#
#   opponent       our WR   n     08-15 field   corpus (n0814)
#   ex_beatdown     0.193  238       27.3%          4.1%
#   dragapult       0.341  264       34.2%          4.4%
#   mixed_ex4       0.371  213       12.8%          5.0%   <- already boosted
#
# Two thirds of the field is two decks we lose to, and the corpus has 8.5% of it.
#
# Deliberately 3x and not more. --opp-mix on 08-14 pushed dragapult 3.7% -> 25.8%
# (about 7x) and measured z -3.06: past some point the reweighting is duplicating
# a handful of games rather than teaching the matchup. 3x keeps every archetype
# inside one order of magnitude of its corpus share.
#
# Two extra gate cells are added against our own ebd and dragapult clones. Those
# clones are weak -- the frozen gate's dragapult opponent scores 0.865 where real
# dragapult players hold us to 0.341 -- so the ABSOLUTE numbers are worthless.
# For a controlled comparison (same corpus, same features, weights only) a weak
# opponent still detects a relative difference, which is exactly the footing the
# x4b3 result stands on.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TAG=f3
echo "=== $TAG : n0814 corpus, ex_beatdown/dragapult/mixed_ex4 rows x3"
uv run python train_gbdt.py --rows n0814 --rounds 900 --out-tag "$TAG" --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 --boost-opp "3:3,4:3,5:3" \
    > "train_${TAG}.log" 2>&1
grep -E "boosting|rows boosted|^  main |overall" "train_${TAG}.log"
uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
uv run python parity_pure.py --tag "$TAG" --rows n0814 --n 150 2>&1 | tail -2
uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -6

echo "  --- frozen gate (bar v059 0.6640, controls n0814 0.6604 / x4b3 0.6806)"
A="build_$TAG/submission.tar.gz"
r() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }
r --n 1200 --artifact "$A" --opp gbdt:build_ex4b/submission.tar.gz > "gg_${TAG}_ex4.log" 2>&1
printf "  mixed_ex4   "; tail -1 "gg_${TAG}_ex4.log"
r --opp ref --n 1200 --artifact "$A" > "gg_${TAG}_mirror.log" 2>&1
printf "  mirror(ref) "; tail -1 "gg_${TAG}_mirror.log"
r --opp alakazam --n 800 --artifact "$A" > "gg_${TAG}_alakazam.log" 2>&1
printf "  alakazam    "; tail -1 "gg_${TAG}_alakazam.log"
r --opp lucario --n 400 --artifact "$A" > "gg_${TAG}_lucario.log" 2>&1
printf "  lucario     "; tail -1 "gg_${TAG}_lucario.log"
for o in crustle dragapult; do
  r --opp $o --n 200 --artifact "$A" > "gg_${TAG}_$o.log" 2>&1
  printf "  %-11s " $o; tail -1 "gg_${TAG}_$o.log"
done
uv run python gate_score.py "$TAG"

echo "  --- off-gate cells (relative only; these clones are weak)"
for SPEC in "ebd:build_ebd" "drg:build_drg"; do
  N=${SPEC%%:*}; B=${SPEC##*:}
  [ -f "$B/submission.tar.gz" ] || { echo "  $N: no artifact, skipped"; continue; }
  for CAND in "$TAG" n0814; do
    r --n 400 --artifact "build_$CAND/submission.tar.gz" \
        --opp "gbdt:$B/submission.tar.gz" > "og_${CAND}_${N}.log" 2>&1
    printf "  %-6s vs %-4s " "$CAND" "$N"; tail -1 "og_${CAND}_${N}.log"
  done
done
echo "=== FIELD3 DONE"
