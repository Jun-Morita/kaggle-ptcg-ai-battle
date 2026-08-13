#!/usr/bin/env bash
# One command per day: fetch yesterday, extend the window by a day, retrain,
# and score on the FROZEN gate.
#
#   ./daily_cycle.sh 2026-08-12 d0812
#
# Frozen on purpose:
#   * the gate opponents, including build_ex4b. A ruler that changes daily makes
#     day-to-day numbers incomparable -- a candidate scoring lower could mean a
#     worse candidate or a stronger opponent, and there is no way to tell. ex4b
#     is a harsh opponent (we beat real Mega Lopunny ex players 7-2 on the ladder
#     while scoring 0.493 against it here), which is the safe direction for a gate.
#   * n per cell, so the standard errors stay the ones already computed.
#   * the window START at 07-28. Rolling it forward cost v12 19% of its decisions
#     and 0.022 of gate; extending is what v13/v14 did.
#
# The weights are NOT frozen, but only change if the observed mix moves by 5pp or
# more -- v057's 77 games and v059's 65 games agreed to within 4pp, so re-deriving
# them daily would be churn.
#
# Bar: beat v059's 0.6640. Submit at most once, on 08-15, and only the best.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAY="${1:?usage: daily_cycle.sh YYYY-MM-DD TAG}"
TAG="${2:?usage: daily_cycle.sh YYYY-MM-DD TAG}"
RAW=/home/jun/kaggle-ptcg-ai-battle/references/raw
SHORT="${DAY:5:2}${DAY:8:2}"

echo "=== 1. fetch $DAY"
if ls "$RAW/episodes_$SHORT"/*.zip >/dev/null 2>&1; then
  echo "  already have it"
else
  mkdir -p "$RAW/episodes_$SHORT"
  (cd "$RAW/episodes_$SHORT" && uv run kaggle datasets download \
      -d "kaggle/pokemon-tcg-ai-battle-episodes-$DAY" -p . 2>&1 | tail -1)
  python3 -c "
import zipfile,glob,sys
z=glob.glob('$RAW/episodes_$SHORT/*.zip')
if not z: sys.exit('  NOT PUBLISHED YET')
print('  ok', len(zipfile.ZipFile(z[0]).namelist()), 'episodes')" || exit 1
fi

echo "=== 2. index"
./scan_new_days.sh 2>&1 | tail -2

echo "=== 3. corpus 07-28..$DAY"
mkdir -p "idx_$TAG" && rm -f "idx_$TAG"/*.json
for f in indices/2026-*.json; do
  d=$(basename "$f" .json)
  [[ "$d" > "2026-07-27" && ! "$d" > "$DAY" ]] && ln -sf "../$f" "idx_$TAG/$d.json"
done
echo "  days: $(ls "idx_$TAG" | wc -l)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck --max-dec 3000000 \
    --out "$TAG" --index "$PWD/idx_$TAG/*.json" > "build_${TAG}.log" 2>&1
grep -E "^target|^decisions" "build_${TAG}.log"

echo "=== 4. train + package"
uv run python train_gbdt.py --rows "$TAG" --rounds 900 --out-tag "$TAG" --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > "train_${TAG}.log" 2>&1
grep -E "train_q|overall" "train_${TAG}.log"
uv run python export_pure.py --tag "$TAG" 2>&1 | tail -2
uv run python parity_pure.py --tag "$TAG" --rows "$TAG" --n 150 2>&1 | tail -2
uv run python build_submission.py --tag "$TAG" --n 25 2>&1 | tail -5

echo "=== 5. frozen gate (bar: v059 = 0.6640)"
A="build_$TAG/submission.tar.gz"
# env -u guards the opponent artifacts: a stray PTCG_DECK_JSON re-featurises the
# OPPONENT's model too, and on 08-12 that produced a 0.991 winrate out of nowhere.
run() { env -u PTCG_DECK_JSON uv run python eval_h2h.py "$@"; }
run --n 1200 --artifact "$A" --opp gbdt:build_ex4b/submission.tar.gz > "gg_${TAG}_ex4.log" 2>&1
printf "  mixed_ex4   "; tail -1 "gg_${TAG}_ex4.log"
run --opp ref --n 1200 --artifact "$A" > "gg_${TAG}_mirror.log" 2>&1
printf "  mirror(ref) "; tail -1 "gg_${TAG}_mirror.log"
run --opp alakazam --n 800 --artifact "$A" > "gg_${TAG}_alakazam.log" 2>&1
printf "  alakazam    "; tail -1 "gg_${TAG}_alakazam.log"
run --opp lucario --n 400 --artifact "$A" > "gg_${TAG}_lucario.log" 2>&1
printf "  lucario     "; tail -1 "gg_${TAG}_lucario.log"
for o in crustle dragapult; do
  run --opp $o --n 200 --artifact "$A" > "gg_${TAG}_$o.log" 2>&1
  printf "  %-11s " $o; tail -1 "gg_${TAG}_$o.log"
done
uv run python gate_score.py "$TAG"
echo "=== DAILY $TAG DONE"
