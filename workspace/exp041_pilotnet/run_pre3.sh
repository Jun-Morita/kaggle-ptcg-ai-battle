#!/usr/bin/env bash
# exp041 pre3 -- two-stage GPU run, prepared 2026-07-10 while GPU was busy.
# PRECONDITION: the 4 grimmsnarl datagen workers (data/grim_w1[0-3].log) must
# print DONE first:   grep -l DONE data/grim_w1*.log | wc -l   -> 4
#
# Stage a (pre3a, safe absorption): continue from pre2 ep8. Adds
#   - grimmsnarl synthetic (new ladder-#1 matchup, ~900k records, w10-13)
#   - ladder_w9 real-meta corpus (45,447 records, x5 oversample via glob repeat)
#   to the 5.9M synthetic base. All value weights = 1 (labels are
#   policy-consistent: v014-lineage actions + real outcomes).
#   Gates: (1) synthetic val top-1 >= 0.82 (no forgetting), (2) eval_raw n=50
#   oracle-free: old-5 total >= pre2's 2.14 AND grimmsnarl measured (ref 0.60).
#
# Stage b (pre3b, expert bet): continue from pre3a. Adds expert_w8 (Yushin's
#   old same-archetype sub, 56,627 records, x10 oversample). His decisions
#   diverge from our net most in the NON-EX MIRROR (top-1 0.402 vs our own
#   0.798) -- exactly his 0.77-vs-our-0.585 edge. Risks known & accepted:
#   deck is the TR-tutor variant (42/60 shared, exp024 deck-x-pilot boundary);
#   transfer relies on the shared Trevenant/Boss/gust core.
#   Gates: (1) expert-holdout top-1 rises materially (0.44 -> 0.55+),
#   (2) synthetic val top-1 >= 0.80, (3) eval_raw n=50 >= pre3a,
#   (4) THE decisive prize check: paired mirror vs v014 (the one matchup BC-of-
#   v014 can never win; expert transfer would show here first).
set -euo pipefail
cd "$(dirname "$0")"

SYN='data/samples_turnbeam_w*.pkl'            # 5.9M base + grimmsnarl w10-13
LAD='data/ladder_w9.pkl'
EXP='data/expert_w8.pkl'

echo "== stage a: pre3a (synthetic+grimmsnarl+ladder x5) =="
uv run python pretrain.py \
  --glob "$SYN,$LAD,$LAD,$LAD,$LAD,$LAD" \
  --resume results/pre2/model_ep8.pth \
  --tag pre3a --epochs 2 --lr 1e-4 --opp-drop 0.3

echo "== stage a gate: eval_raw n=50 oracle-free =="
uv run python eval_raw.py results/pre3a/model_ep1.pth --n 50 --oracle-free

echo "== stage b: pre3b (+expert x10) =="
uv run python pretrain.py \
  --glob "$SYN,$LAD,$LAD,$LAD,$LAD,$LAD,$EXP,$EXP,$EXP,$EXP,$EXP,$EXP,$EXP,$EXP,$EXP,$EXP" \
  --resume results/pre3a/model_ep1.pth \
  --tag pre3b --epochs 2 --lr 5e-5 --opp-drop 0.3

echo "== stage b gate: eval_raw n=50 oracle-free =="
uv run python eval_raw.py results/pre3b/model_ep1.pth --n 50 --oracle-free

echo "ALL DONE -- next: expert-holdout top-1 via diag_realgap.py, then paired mirror vs v014"
