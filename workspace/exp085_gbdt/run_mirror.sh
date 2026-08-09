#!/usr/bin/env bash
# A real mirror gate -- and a validation of it before we trust it.
#
# Why: /meta-watch on v054 shows 42% of our ladder games are the Grimmsnarl
# (オーロンゲ) mirror, and our field gate measures that cell against OURSELVES,
# which is 0.500 by construction and carries no information. The largest cell we
# play is the one cell we cannot see. tetsutani's public agent runs a 60/60
# IDENTICAL decklist, so it is a genuine mirror opponent.
#
# Why validate first: exp084 already used this reference as a gate and it FAILED
# to reproduce ladder order on the transformer builds (0.325 / 0.467 / 0.392
# against ladder 873 / 803 / 745). Two of our GBDT builds now have settled ladder
# scores, so the gate can be checked against them before it selects anything:
#
#     build_v4b (v053)  ladder 867.3
#     build_v6  (v054)  ladder 954.2
#
# If the reference ranks v4b below v6, the gate has predictive value for this
# model family and we can use it on v055. If it does not, it stays closed.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for b in v4b v6 v7m1075; do
  echo "=== build_$b vs the tetsutani reference (true mirror), n=400"
  uv run python eval_h2h.py --opp ref --n 400 \
      --artifact build_$b/submission.tar.gz > mir_$b.log 2>&1
  printf "  %-9s" $b; tail -1 mir_$b.log
done
echo "=== MIRROR GATE DONE"
