#!/usr/bin/env bash
# 1) Settle the mirror disagreement at a usable sample size, then 2) the
# per-family capacity sweep.
#
# The mirror gate ordered the two builds whose ladder scores we know correctly
# (v4b 0.535 -> 867.3, v6 0.560 -> 954.2) and then put v7m1075 LAST at 0.522 --
# while the weighted field gate calls v7m1075 the best of the three. The mirror
# is 42% of our real games, so this disagreement decides whether v055 is actually
# an improvement. n=400 leaves it at z~1.1; n=1000 is worth the 15 minutes.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for b in v6 v7m1075; do
  echo "=== build_$b vs reference, n=1000"
  uv run python eval_h2h.py --opp ref --n 1000 \
      --artifact build_$b/submission.tar.gz > mirbig_$b.log 2>&1
  printf "  %-9s" $b; tail -1 mirbig_$b.log
done
echo "=== direct: v7m1075 vs v6, n=800"
uv run python eval_h2h.py --n 800 --artifact build_v7m1075/submission.tar.gz \
    --opp gbdt:build_v6/submission.tar.gz > h2h_1075_vs_v6_n800.log 2>&1
tail -1 h2h_1075_vs_v6_n800.log

exec ./run_v13.sh
