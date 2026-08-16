#!/usr/bin/env bash
# The v9b recipe, brought forward to 08-15. The one hypothesis the gate has been
# arguing against all week, and the only one the LADDER supports.
#
#   v9b   07-01..08-08   38 days   44,327 seats   2,091,779 decisions
#         gate 0.6342 -- last of every build measured
#         ladder 931 / 933 / 880 / 921 -- first of every build measured
#
# Everything since 08-11 has started the window at 07-28 (12-19 days, 1.2-1.45M
# decisions) because each extension scored lower on the gate. But the gate ranks
# v9b last and the ladder ranks it first, so "the gate says stop adding data" is
# not evidence about the ladder. This build follows the ladder instead: keep July,
# add the seven days v9b never saw.
#
#   w45   07-01..08-15   46 days   48,787 seats   (+10% seats over v9b)
#
# 361 columns (USE_OPP_CARDS off), so it is comparable to n0814 / n0815 and to
# v9b's 360 -- the one column between them is teacher_pct, added after v9b.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAG=w45

mkdir -p "idx_$TAG" && rm -f "idx_$TAG"/*.json
for f in indices/2026-*.json; do
  d=$(basename "$f" .json)
  [[ "$d" > "2026-06-30" && ! "$d" > "2026-08-15" ]] && ln -sf "../$f" "idx_$TAG/$d.json"
done
echo "=== $TAG  days: $(ls "idx_$TAG" | wc -l)"

uv run python build_rows.py --arch mixed_ex3 --exact-deck --max-dec 3000000 \
    --out "$TAG" --index "$PWD/idx_$TAG/*.json" > "build_${TAG}.log" 2>&1
grep -E "^target|^decisions" "build_${TAG}.log"

uv run python train_gbdt.py --rows "$TAG" --rounds 900 --out-tag "$TAG" --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > "train_${TAG}.log" 2>&1
grep -E "^  main |overall" "train_${TAG}.log"
uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
uv run python parity_pure.py --tag "$TAG" --rows "$TAG" --n 150 2>&1 | tail -2
uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -6

echo "=== frozen gate (bar: v059 = 0.6640)"
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
echo "=== W45 DONE"
