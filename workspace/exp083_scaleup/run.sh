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
CORPUS_V3=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mixed_ex3v3wl_multi_w7.pkl
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
  # DISTIL: the whole point of exp083b. A3 (d256/2+2) got genuinely stronger
  # (0.665 vs the old net, z=+4.67) but cannot ship -- no numpy in the sandbox
  # (v015/v042) and ~0.7s/act in pure python. d128ctl CAN ship but was FLAT
  # (0.525) despite better label top-1. So: keep the shippable student exactly as
  # it is (d128/h2/1+1, 47.9MB, 0.29s/act, byte-identical npmcts_policy.py) and
  # change only what it is trained to imitate -- A3's full output vector instead
  # of the one-hot human pick. Same recipe as d128ctl otherwise, so the two runs
  # differ ONLY in the target and are directly comparable.
  DISTIL) uv run python pretrain.py --glob "$CORPUS" --tag sc083_distil --epochs 24 \
        --d-model 128 --heads 2 --enc-layers 1 --dec-layers 1 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 \
        --teacher results/sc083_A3/model_ep23.pth --distill 0.7 ;;
  # DEEP: only became shippable after item-3 halved the pure-python forward
  # (126 -> 69 ms/decision, max_act 0.29 -> 0.15s). Keeps d_model=128 -- so the
  # weight file stays in the ~51MB range that has actually shipped -- and buys
  # capacity in the LAYERS instead, where the cost is compute (now affordable)
  # rather than file size (vocab x d_model dominates the bytes). Distilled from
  # A3 as well, since that target beat hard labels at fixed capacity.
  DEEP) uv run python pretrain.py --glob "$CORPUS" --tag sc083_deep --epochs 24 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 \
        --teacher results/sc083_A3/model_ep23.pth --distill 0.7 ;;
  # V3T: the exp083c teacher -- all three of today's defects fixed at once.
  #  (1) ENC_V3 features: the v1 encoder never showed the net supporterPlayed /
  #      energyAttached / stadiumPlayed / retreated / maxHp / appearThisTurn /
  #      preEvolution / energy types / faceup prizes / looking cards. Legality is
  #      enforced by the candidate list so nothing ever crashed -- evaluation and
  #      within-turn sequencing were just starved.
  #  (2) --keep-losses corpus: the old one was WON-games-only, so every outcome
  #      label was +1 and the value head learned a constant (stdev 2e-5). Now
  #      1.95M records / 22,830 games (1.8x), outcomes 55/45.
  #  (3) --policy-loss margin: only penalise candidates ranked ABOVE the observed
  #      move. The player picks from the cards they happened to draw, so the other
  #      ~5 candidates are not known-bad; hard -1 on all of them overclaims.
  # Steps are matched to A3's budget (24*8044=193k) at the new corpus size.
  V3T) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_V3" --tag sc083_v3t --epochs 16 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch 14467 --seed 42 --policy-loss margin ;;
  # V3S: the shippable student -- same d128/h4/2+2 as sc083_deep (48.9MB,
  # max_act 0.35s) so the ONLY differences vs deep are the three exp083c fixes
  # carried in through the teacher + corpus. That keeps gate 2 (V3S vs deep) a
  # clean read on whether the fixes buy real playing strength.
  V3S) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_V3" --tag sc083_v3s --epochs 16 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch 14467 --seed 42 --policy-loss margin \
        --teacher results/sc083_v3t/model_ep15.pth --distill 0.7 ;;
  B)  uv run python pretrain.py --glob "$CORPUS" --tag sc083_B --epochs 24 \
        --d-model 384 --heads 6 --enc-layers 4 --dec-layers 4 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 ;;
esac
