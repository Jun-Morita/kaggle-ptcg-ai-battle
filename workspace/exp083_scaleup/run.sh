#!/usr/bin/env bash
# exp083 scale-up BC training. Run from workspace/exp041_pilotnet (pretrain.py's HERE).
# Checkpoints/history land in exp041_pilotnet/results/<tag>/.
#
# A  (no warmup)  = FAILED to optimise: post-norm at 2+2 layers plateaued at acc 0.586
#                   by ep2 and stalled, never reaching the d128 baseline's 0.624.
# A2 (warmup)     = same arch, +4000-step linear warmup then cosine. Isolates the
#                   optimisation variable against A.
set -euo pipefail
CORPUS=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mixed_ex3_multi_w7.pkl
SPE=8044   # batches/epoch for the 10-day corpus at bs=128 (measured)
cd "$(dirname "$0")/../exp041_pilotnet"

case "${1:-A2}" in
  A)  uv run python pretrain.py --glob "$CORPUS" --tag sc083_A --epochs 24 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 \
        --opp-drop 0.5 --batch-size 128 --cosine --seed 42 ;;
  A2) uv run python pretrain.py --glob "$CORPUS" --tag sc083_A2 --epochs 24 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 ;;
  # A3 = the recipe that actually optimises. LR 3e-4 (the official sample's value,
  # fine for d128/1+1) is too hot for d256/2+2: it plateaued (A) or oscillated (A2).
  # An LR probe at 1e-4 + grad-clip reached 0.6255 by epoch 1, above the d128
  # baseline's 3-epoch best (0.6240), and stayed stable.
  A3) uv run python pretrain.py --glob "$CORPUS" --tag sc083_A3 --epochs 24 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 ;;
  B)  uv run python pretrain.py --glob "$CORPUS" --tag sc083_B --epochs 24 \
        --d-model 384 --heads 6 --enc-layers 4 --dec-layers 4 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 ;;
esac
