#!/usr/bin/env bash
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PTCG_DECK_JSON="$PWD/deck_mixed_ex4.json"
uv run python train_gbdt.py --rows ex4 --rounds 900 --out-tag ex4 \
    --leaves main=511,c7=255,mid=127,low=63,easy=31 --seed 0
