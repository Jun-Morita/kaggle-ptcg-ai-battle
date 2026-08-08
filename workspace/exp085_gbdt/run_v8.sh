#!/usr/bin/env bash
# Teacher quality WON at >=1100: judged on the same 118,681 held-out decisions
# from the whole teacher population, dropping 53.5% of rows raised overall top-k
# 0.7836 -> 0.7910 and every family improved (c7 +0.0163). It collapses at 1150
# (0.7213) where main's training set falls to 40k queries, so the quality/quantity
# crossover sits near 1100. This brackets it with 1075 and 1125, then puts the
# winner through the ship path and the weighted field gate against the SHIPPED
# v6 build (= v054).
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for TH in 1075 1125; do
  echo "=== train min-score $TH"
  uv run python train_gbdt.py --rows v7 --rounds 900 --min-score $TH \
      --out-tag v7m$TH 2>&1 | grep -v "LightGBM\]" | tail -8
done

echo "=== all thresholds on ONE held-out set (all teachers)"
uv run python eval_fixed.py --rows v7 \
    --tags v7,v7m1050,v7m1075,v7m1100,v7m1125,v7m1150 2>&1 | grep -v "LightGBM\]"
echo "=== V8 EVAL DONE"
