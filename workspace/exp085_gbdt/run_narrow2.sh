#!/usr/bin/env bash
# Is the final weekend's data actually better, or just newer?
#
# The recent-only corpora were rejected hard on 08-15 -- r10 (08-05..08-14) at
# z -2.97 and r7 (08-08..08-14) at z -6.19 -- and the pattern was monotone in
# decision count, which reads as "volume wins". But every one of those runs also
# changed the volume, so "newer is better" was never measured on its own.
#
# These two hold the WINDOW LENGTH fixed and slide it one day later, so the only
# thing that moves is which day the data comes from:
#
#   r7   08-08..08-14   7d   0.5886      r7n   08-09..08-15   7d
#   r10  08-05..08-14  10d   0.6279      r10n  08-06..08-15  10d
#
# The prior is weak: 08-15 contributes 189 mixed_ex3 teacher seats, about 5% of a
# seven-day window, because our archetype collapsed to 6.1% of the field. Five
# percent of the corpus cannot move 0.075 of gate. What this does buy is a clean
# reading on direction -- if both shifted windows come in ABOVE their originals,
# freshness is worth something and the volume story is incomplete.
#
# 361 columns, same seed, same leaves, same frozen gate, bar v059 = 0.6640.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_one() {
  local TAG="$1" FROM="$2" TO="$3" PREV="$4"
  echo "=== $TAG : $FROM .. $TO   (paired with $PREV)"
  mkdir -p "idx_$TAG" && rm -f "idx_$TAG"/*.json
  for f in indices/2026-*.json; do
    d=$(basename "$f" .json)
    [[ ! "$d" < "$FROM" && ! "$d" > "$TO" ]] && ln -sf "../$f" "idx_$TAG/$d.json"
  done
  echo "  days: $(ls "idx_$TAG" | wc -l)"
  uv run python build_rows.py --arch mixed_ex3 --exact-deck --max-dec 3000000 \
      --out "$TAG" --index "$PWD/idx_$TAG/*.json" > "build_${TAG}.log" 2>&1
  grep -E "^target|^decisions" "build_${TAG}.log"
  uv run python train_gbdt.py --rows "$TAG" --rounds 900 --out-tag "$TAG" --seed 0 \
      --leaves main=255,c7=127,mid=127,low=63,easy=31 > "train_${TAG}.log" 2>&1
  grep -E "^  main |overall" "train_${TAG}.log"
  uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
  uv run python parity_pure.py --tag "$TAG" --rows "$TAG" --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -6

  echo "  --- frozen gate"
  local A="build_$TAG/submission.tar.gz"
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
  echo "=== $TAG DONE"
}

run_one r10n 2026-08-06 2026-08-15 "r10 0.6279"
run_one r7n  2026-08-09 2026-08-15 "r7  0.5886"
echo "=== NARROW2 DONE"
