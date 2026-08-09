#!/usr/bin/env bash
# Export -> parity -> smoke -> paired head-to-head vs the v054 build.
# The v054 build is build_v6/submission.tar.gz (v6 featuriser+corpus is what
# shipped as v054). n=1600 because the observed se at n=200 is 0.028; two runs of
# the SAME build once gave 0.512 and 0.536, so anything under n>=1600 cannot see
# the size of difference we are looking for.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for T in v9a v9b; do
  echo "=== export $T"
  uv run python export_pure.py --tag $T 2>&1 | tail -4
  uv run python parity_pure.py --tag $T --rows v9 --n 150 2>&1 | tail -3
  uv run python build_submission.py --tag $T --n 25 2>&1 | tail -6
done
for T in v9a v9b; do
  echo "=== $T vs the v054 build, n=1600"
  uv run python eval_h2h.py --n 1600 --artifact build_$T/submission.tar.gz \
      --opp gbdt:build_v6/submission.tar.gz > h2h_${T}_vs_v6.log 2>&1
  tail -1 h2h_${T}_vs_v6.log
done
echo "=== V19 DONE"
