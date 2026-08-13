#!/usr/bin/env bash
# An ex_beatdown opponent for the gate.
#
# ex_beatdown went 5.6% of the field on 08-01 to 20.6% on 08-12 -- second only to
# dragapult -- and the gate has no cell for it. Our only evidence is 1-1 on the
# ladder. That is the same blind spot mixed_ex4 was on 08-11, and closing that
# one reversed six rejections.
#
# Same construction as ex4b: find the archetype's most common exact 60, keep
# teachers within 58/60 of it, train the five-family ranker, package it as an
# artifact. It does not need to be a good agent -- it needs to be a faithful
# ex_beatdown, and a slightly-too-strong opponent errs in the safe direction.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -qE "DAILY d0812 DONE|NOT PUBLISHED" daily_d0812.log 2>/dev/null; do sleep 120; done

echo "=== 1. what is ex_beatdown, exactly?"
uv run python probe_arch.py --arch ex_beatdown --days 08-08,08-09,08-10,08-11,08-12 \
    --cap 500 2>&1 | tail -30

export PTCG_DECK_JSON="$PWD/deck_ex_beatdown.json"
echo "=== 2. corpus"
uv run python build_rows.py --arch ex_beatdown --exact-deck --near 58 \
    --deck deck_ex_beatdown.json --max-dec 3000000 --out ebd \
    --index "$PWD/indices/*.json" > build_ebd.log 2>&1
grep -E "^target|near-deck|^decisions|^skips" build_ebd.log

echo "=== 3. train + package"
uv run python train_gbdt.py --rows ebd --rounds 900 --out-tag ebd --seed 0 \
    --leaves main=255,c7=127,mid=127,low=63,easy=31 > train_ebd.log 2>&1
grep -E "train_q|overall" train_ebd.log
uv run python export_pure.py --tag ebd 2>&1 | tail -2
uv run python parity_pure.py --tag ebd --rows ebd --n 150 2>&1 | tail -2
uv run python build_submission.py --tag ebd --n 25 --deck deck_ex_beatdown.json 2>&1 | tail -5

echo "=== 4. the new cell, for every build still in play"
for T in v10rL v13 v9b; do
  env -u PTCG_DECK_JSON uv run python eval_h2h.py --n 1200 \
      --artifact build_$T/submission.tar.gz \
      --opp gbdt:build_ebd/submission.tar.gz > gg_${T}_ebd.log 2>&1
  printf "  %-6s vs ex_beatdown  " $T; tail -1 gg_${T}_ebd.log
done
echo "=== V36 DONE"
