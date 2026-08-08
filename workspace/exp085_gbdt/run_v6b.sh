#!/usr/bin/env bash
# Export / parity / build both v6 variants, then the deciding test: each built
# artifact against the SHIPPED v4b build (v053), seats alternated.
#
# The held-out top-k cannot decide this. v6s and v6 were scored on a different
# validation set from v4b's (a bigger corpus has a different last 10%), and
# exp085 already has one case -- v5 -- where the offline number was the highest of
# the lot and the direct head-to-head against our own build was 0.467.
set -u
cd "$(dirname "$0")"

for t in v6s v6; do
  echo "=== $t export"; uv run python export_pure.py --tag $t 2>&1 | tail -7
done

echo "=== v6s parity (model is 318 wide, corpus is 336)"
uv run python parity_pure.py --tag v6s --rows v6 --n 150 --n-feat 318 2>&1 | tail -4
echo "=== v6 parity"
uv run python parity_pure.py --tag v6 --rows v6 --n 150 2>&1 | tail -4

for t in v6s v6; do
  echo "=== $t build + smoke"; uv run python build_submission.py --tag $t --n 25 2>&1 | tail -10
done

echo "=== head to head vs the shipped v4b build (v053), n=300"
for t in v6s v6; do
  uv run python eval_h2h.py --n 300 --artifact build_$t/submission.tar.gz \
      --opp gbdt:build_v4b/submission.tar.gz > h2h_${t}_vs_v4b.log 2>&1
  printf "%-5s vs v4b  " $t; tail -1 h2h_${t}_vs_v4b.log
done
echo "=== V6B DONE"
