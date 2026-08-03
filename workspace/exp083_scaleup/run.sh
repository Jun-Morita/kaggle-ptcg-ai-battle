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
# 15-day rebuild (07-13..07-27). 3,545,132 records / 41,188 games -- 1.8x the 10-day
# corpus, and it now spans the window in which Grimmsnarl went 17% -> 51% of the top
# band. 46% of the records are mirror games, which is exactly the matchup v044 lost
# (0.25). Same ENC_V3 + --keep-losses flags as CORPUS_V3, so V15* differ from V3*
# ONLY in how much (and how recent) the teacher data is.
CORPUS_V15=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mix15v3wl_multi_w7.pkl
SPE15=27000
# Elite corpus: teachers with LB score >= 1100 (top 20 teams) instead of >= 1000
# (118 teams). 855,593 records / 9,333 games; 59% mirror.
CORPUS_E11=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/elite11_multi_w7.pkl
SPE11=6684
# 28-day corpus (07-01..07-28). Two things change at once vs the 15/16-day builds,
# both in the direction the field gate says we need: (a) Mega Lucario ex is present
# at 3.4-20% of teacher seats in 07-03..07-12 and at 0% from 07-13 on, and it is our
# worst matchup on the ladder (v3s 0.45, v046 0.27) while being 6-22% of our games;
# (b) mirror share falls -- the recent days run 50-67% mirror and the older ones
# 0-35%, and mirror over-representation is what made v046 worse in the field.
# Built with ENC_V3, not V4, so the only difference vs v3s (our strongest net) is
# the teacher data.
CORPUS_28=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mix28v3wl_multi_w7.pkl
SPE28=38000
# exp083m: the same 28 days, plus the seats we always threw away. build_multi.py
# only ever kept seats playing OUR archetype, so no position was ever labelled from
# an Alakazam / Crustle / Lucario player's own point of view -- and MCTS asks the net
# for exactly that at every opponent node. seat* files train the VALUE head only
# (pretrain.is_value_only); their moves are not our moves.
#   mix28  4,904,410 decisions   Grimmsnarl, policy + value
#   seat   4,585,976 decisions   Alakazam 3.70M / Crustle 0.81M / Lucario 0.08M, value
# SPE is doubled so the policy head still gets the same 228k Grimmsnarl steps as
# D28S; otherwise "added value data" and "halved the policy budget" would be one
# change measured as one number.
CORPUS_28M="/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mix28v3wl_multi_w7.pkl,/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/seat28*_multi_w7.pkl"
SPE28M=76000
# exp083n: an Alakazam PILOT (policy + value), not a value donor. The gate's
# opponents are all rule-based and we beat four of six at 0.89-0.99, so it cannot
# separate candidates -- the same agent scores 0.55 on the real ladder. Alakazam is
# 27.6% of our score band (public score-band snapshot) and we have 3.7M of its
# decisions with policy labels that the seat* path deliberately throws away. Same
# file, hardlinked under a "pilot" name so is_value_only() does not fire.
CORPUS_CRUS=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/pilot28crusv3wl_multi_w7.pkl
CORPUS_EX1=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/pilot28ex1v3wl_multi_w7.pkl
CORPUS_28A="/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mix28v3wl_multi_w7.pkl,/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/seat28ex1v3wl_multi_w7.pkl"
CORPUS_V4=/home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/mix16v4wl_multi_w7.pkl
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
  # V15T / V15S: identical recipe to V3T / V3S, only the corpus changes (10d -> 15d).
  # Step budget is held near V3T's 231k (8 * 27000 = 216k) so the comparison reads as
  # "more/fresher data at the same compute", not "trained longer".
  V15T) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_V15" --tag sc083_v15t --epochs 8 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE15 --seed 42 --policy-loss margin ;;
  V15S) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_V15" --tag sc083_v15s --epochs 8 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE15 --seed 42 --policy-loss margin \
        --teacher results/sc083_v15t/model_ep7.pth --distill 0.7 ;;
  # E11T / E11S (exp083g): the OTHER axis -- teacher QUALITY instead of quantity.
  # V15* asked "more data"; this asks "better data". min_score 1000 -> 1100 cuts the
  # teacher pool from 118 teams to the top 20, i.e. the actual ladder frontier (our
  # target, the silver cut, is 916.7). Cost: 855,593 records / 9,333 games, a quarter
  # of the 15-day corpus. 59% of it is mirror, matching the top band being 51%
  # Grimmsnarl -- the matchup v045 is still losing (0.45).
  E11T) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_E11" --tag sc083_e11t --epochs 24 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE11 --seed 42 --policy-loss margin ;;
  # E11T's val curve PEAKS at epoch 9 (0.7553) and then DECLINES to 0.747-0.750 by
  # ep18 -- 855k records cannot absorb 24 epochs. So the student distils from ep9,
  # not the last checkpoint, and gets a matched 10-epoch budget.
  E11S) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_E11" --tag sc083_e11s --epochs 10 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE11 --seed 42 --policy-loss margin \
        --teacher results/sc083_e11t/model_ep9.pth --distill 0.7 ;;
  # V15S2: V15S was cut off half-trained. Its 8-epoch curve (0.7196 -> 0.7501)
  # overlays V3S's first 8 (0.7107 -> 0.7497) almost exactly, and V3S went on to
  # 0.7577 over 16 -- yet V15S ALREADY beats V3S head-to-head 0.608 (z=+4.30) at
  # half the budget. A warm restart (SGDR-style second cosine cycle at half the
  # peak LR, no warmup since the net is already conditioned) buys the missing half
  # for 8 epochs instead of retraining 16 from scratch.
  V15S2) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_V15" --tag sc083_v15s2 --epochs 8 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 5e-5 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine \
        --steps-per-epoch $SPE15 --seed 43 --policy-loss margin \
        --resume results/sc083_v15s/model_ep7.pth \
        --teacher results/sc083_v15t/model_ep7.pth --distill 0.7 ;;
  # V15E: quality and quantity are not exclusive -- this is the curriculum version.
  # Start from V15S2 (broad: 41,188 games from 118 teams >= 1000) and finish on the
  # elite corpus (9,333 games from the top 20 teams >= 1100) at a low LR. The broad
  # pass supplies coverage; the elite pass shifts the net toward how the actual
  # ladder frontier plays. Low LR + 3 epochs because exp083e showed what happens
  # when a short fine-tune is allowed to overwrite a well-conditioned policy head.
  V15E) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_E11" --tag sc083_v15e --epochs 3 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 2e-5 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine \
        --steps-per-epoch $SPE11 --seed 44 --policy-loss margin \
        --resume results/sc083_v15s2/model_ep7.pth \
        --teacher results/sc083_e11t/model_ep9.pth --distill 0.7 ;;
  # V4T / V4S (exp083h): ENC_V4 -- the encoder audit result. Same 15-day window and
  # same recipe as V15T/V15S, so the ONLY variable is the two new feature words:
  #   word 26 = obs.select (what the engine is asking: type, context, min/maxCount,
  #             remainDamageCounter, remainEnergyCost, contextCard, effect). The
  #             encoder had none of this -- the state vector was identical whether
  #             the question was "attach energy where" or "place how many counters",
  #             and the value head has no decoder input to disambiguate it.
  #   word 27 = obs.logs (events since the previous selection: log types, coin
  #             flips, damage values, card ids split by actor). Unused ANYWHERE in
  #             the codebase before this.
  # Verified before training: max index 35720 of 38000, 28 words, and train-vs-ship
  # feature parity index-for-index on 300 real positions (parity_enc.py).
  V4T) ENC_V4=1 uv run python pretrain.py --glob "$CORPUS_V4" --tag sc083_v4t --epochs 8 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE15 --seed 42 --policy-loss margin ;;
  V4S) ENC_V4=1 uv run python pretrain.py --glob "$CORPUS_V4" --tag sc083_v4s --epochs 8 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE15 --seed 42 --policy-loss margin \
        --teacher results/sc083_v4t/model_ep7.pth --distill 0.7 ;;
  # D28T / D28S (exp083k): the 28-day corpus. Step budget 6*38000 = 228k, matched to
  # V3T's 231k so this reads as "different teacher data", not "trained longer".
  D28T) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28" --tag sc083_d28t --epochs 6 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28 --seed 42 --policy-loss margin ;;
  D28S) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28" --tag sc083_d28s --epochs 6 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28 --seed 42 --policy-loss margin \
        --teacher results/sc083_d28t/model_ep5.pth --distill 0.7 ;;
  # D28MT / D28MS (exp083m): D28T/D28S with the other seats' value labels added.
  # The teacher is retrained too -- distilling the student's value against a teacher
  # that has never seen those positions would put a guess where the real outcome is.
  D28MT) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28M" --tag sc083_d28mt --epochs 6 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28M --seed 42 --policy-loss margin ;;
  D28MS) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28M" --tag sc083_d28ms --epochs 6 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28M --seed 42 --policy-loss margin \
        --teacher results/sc083_d28mt/model_ep5.pth --distill 0.7 ;;
  # D28MSN: the same student with NO distillation. D28MT came out BELOW the old
  # D28T on every own-seat metric (top-1 0.7394 vs 0.7412, value AUC q1 0.619 vs
  # 0.649), so if D28MS disappoints there are two candidate causes -- the seat data
  # itself, or a teacher that got worse. Distilling at 0.7 puts most of the target
  # in the teacher's hands, so this separates them. Runs concurrently: the 128-wide
  # student leaves the GPU at ~35%.
  D28MSN) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28M" --tag sc083_d28msn --epochs 6 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28M --seed 42 --policy-loss margin ;;
  CRUST) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_CRUS" --tag sc083_crust --epochs 6 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 2000 \
        --steps-per-epoch 8000 --seed 42 --policy-loss margin ;;
  EX1T) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_EX1" --tag sc083_ex1t --epochs 6 \
        --d-model 256 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28 --seed 42 --policy-loss margin ;;
  EX1S) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_EX1" --tag sc083_ex1s --epochs 6 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28 --seed 42 --policy-loss margin \
        --teacher results/sc083_ex1t/model_ep5.pth --distill 0.7 ;;
  # D28MSA: seats from Alakazam ONLY. It is 25% of the ladder and 81% of the seat
  # records; Crustle (0.81M) and Lucario (0.08M) may be adding dilution without
  # adding coverage. Same policy budget as the others.
  D28MSA) ENC_V3=1 uv run python pretrain.py --glob "$CORPUS_28A" --tag sc083_d28msa --epochs 6 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE28M --seed 42 --policy-loss margin ;;
  # SP (exp083e): the AlphaZero improvement step. sc083_v3s played 800 games against
  # itself with sc16 search; selfplay_gen.py kept the SEARCH's per-candidate advantage
  # (record element 12) as a SOFT policy target and the TD-blended root value as the
  # value target. Search beats this same net 0.825 head-to-head, so those labels are a
  # strictly better policy than the net that produced them -- this trains the net
  # toward it. Huber (not margin): margin needs one observed pick, and would throw the
  # soft distribution away. Low LR + 4 epochs on 162k records: the point is to move the
  # net toward the search, not to retrain it and forget the BC corpus.
  SP) ENC_V3=1 uv run python pretrain.py \
        --glob /home/jun/kaggle-ptcg-ai-battle/workspace/exp080_bc/data/spfix_v3s_w0.pkl \
        --tag sc083_sp --epochs 4 \
        --d-model 128 --heads 4 --enc-layers 2 --dec-layers 2 --lr 2e-5 --clip 1.0 \
        --opp-drop 0.0 --batch-size 128 --cosine --steps-per-epoch 1250 --seed 42 \
        --policy-loss huber --resume results/sc083_v3s/model_ep15.pth ;;
  B)  uv run python pretrain.py --glob "$CORPUS" --tag sc083_B --epochs 24 \
        --d-model 384 --heads 6 --enc-layers 4 --dec-layers 4 --lr 1e-4 --clip 1.0 \
        --opp-drop 0.5 --batch-size 128 --cosine --warmup-steps 4000 \
        --steps-per-epoch $SPE --seed 42 ;;
esac
