#!/usr/bin/env bash
# The cell the gate never had. mixed_ex4 is 16% of the games our shipped build
# actually plays on the ladder and we are 6-6 in them, while Archaludon -- weight
# 0.163 in the old gate -- did not appear once in 77 games.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for T in v9b v10rL v11p00; do
  uv run python eval_h2h.py --n 400 --artifact build_$T/submission.tar.gz \
      --opp gbdt:build_ex4b/submission.tar.gz > g_${T}_ex4.log 2>&1
  printf "  %-8s vs mixed_ex4  " $T; tail -1 g_${T}_ex4.log
done
echo "=== V27 DONE"
