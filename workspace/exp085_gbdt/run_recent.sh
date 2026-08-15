#!/usr/bin/env bash
# Recent-only corpora: does teacher freshness beat teacher volume?
#
# Every extension so far has held the window START at 07-28 and added days at
# the end. That kept the volume but also kept 07-28's 2,725 seats, which were
# played in a field that no longer exists (mixed_ex3 33.3% then, 12.1% on 08-14;
# dragapult 8.1% -> 27.6%). The hypothesis is that those early seats are now
# teaching the wrong matchups.
#
# The counter-evidence is v12, the one time the window was rolled forward: it
# lost 19% of its decisions and 0.022 of gate. A recent-only window loses far
# more than 19%, so this only wins if freshness is worth a lot.
#
#   r10   08-05..08-14   6,722 seats   ~470k decisions   38% of v059
#   r7    08-08..08-14   3,525 seats   ~245k decisions   20% of v059
#
# Same frozen gate and same bar as the daily cycle: v059 = 0.6640.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_one() {
  local TAG="$1" FROM="$2" TO="$3"
  echo "=== $TAG : $FROM .. $TO"
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
  grep -E "train_q|overall" "train_${TAG}.log"
  uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
  uv run python parity_pure.py --tag "$TAG" --rows "$TAG" --n 150 2>&1 | tail -2
  uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -5

  echo "  --- frozen gate (bar: v059 = 0.6640)"
  local A="build_$TAG/submission.tar.gz"
  # env -u: a stray PTCG_DECK_JSON re-featurises the OPPONENT's model too.
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

run_one r10 2026-08-05 2026-08-14
run_one r7  2026-08-08 2026-08-14
echo "=== RECENT DONE"
