#!/usr/bin/env bash
# Build a mixed_ex4 (Mega Lopunny ex / メガミミロップex) OPPONENT for the gate.
#
# The ladder record for our shipped build says mixed_ex4 is 16% of the games we
# actually play and we go 6-6 against it, yet the gate has no cell for it at all
# -- while Archaludon, which we did not meet once in 77 games, carries weight
# 0.163. The model trained on 08-09 was rejected as OUR agent (top-k 0.586); as
# an opponent it is the real thing, so it gets reused rather than rebuilt.
#
# It has to be re-made because feats gained the teacher_pct column since: the
# stored ex4 corpus is 366 wide and today's featuriser emits 367.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PTCG_DECK_JSON="$PWD/deck_mixed_ex4.json"
uv run python build_rows.py --arch mixed_ex4 --exact-deck --deck deck_mixed_ex4.json \
    --max-dec 2000000 --out ex4b --index "$PWD/indices/*.json" > build_ex4b.log 2>&1
grep -E "^target|^decisions" build_ex4b.log
uv run python train_gbdt.py --rows ex4b --rounds 900 --out-tag ex4b --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_ex4b.log 2>&1
grep -E "train_q|overall" train_ex4b.log
uv run python export_pure.py --tag ex4b 2>&1 | tail -2
uv run python parity_pure.py --tag ex4b --rows ex4b --n 150 2>&1 | tail -2
uv run python build_submission.py --tag ex4b --n 25 --deck deck_mixed_ex4.json 2>&1 | tail -6
echo "=== V26 DONE"
