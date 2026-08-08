#!/usr/bin/env bash
# Ship gate, weighted by the ladder-band shares in exp083_scaleup/gate_field.py:
#   mixed_ex1 (Alakazam) .276 | mirror .237 | archaludon .163
#   crustle .120 | lucario_ex .039 | dragapult .035
#
# Two corrections this run makes to the earlier read:
#   - Alakazam is the BIGGEST cell and was not measured at all. The 4-opponent
#     field spread covers 36% of the weight.
#   - lucario_v2 is 3.9%, not the dominant share. Its -0.095 matters far less
#     than the unmeasured 27.6%.
# Also gates the seed ensemble (v6e) on the same cells, and re-measures lucario
# at n=600 because the n=200 gap (z~2.0) is the one cell where v6 went backwards.
set -u
cd "$(dirname "$0")"
for t in v6 v6e; do
  echo "=== $t alakazam n=400"
  uv run python eval_h2h.py --opp alakazam --n 400 --artifact build_$t/submission.tar.gz \
      > gf_${t}_alakazam.log 2>&1
  printf "  %-4s alakazam  " $t; tail -1 gf_${t}_alakazam.log
  echo "=== $t lucario n=600"
  uv run python eval_h2h.py --opp lucario --n 600 --artifact build_$t/submission.tar.gz \
      > gf_${t}_lucario.log 2>&1
  printf "  %-4s lucario   " $t; tail -1 gf_${t}_lucario.log
done
echo "=== v4b alakazam n=400 (the incumbent's missing cell)"
uv run python eval_h2h.py --opp alakazam --n 400 --artifact build_v4b/submission.tar.gz \
    > gf_v4b_alakazam.log 2>&1
tail -1 gf_v4b_alakazam.log
echo "=== v4b lucario n=600"
uv run python eval_h2h.py --opp lucario --n 600 --artifact build_v4b/submission.tar.gz \
    > gf_v4b_lucario.log 2>&1
tail -1 gf_v4b_lucario.log
echo "=== v6e remaining cells n=200"
for o in crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact build_v6e/submission.tar.gz > gv6e_$o.log 2>&1
  printf "  %-11s" $o; tail -1 gv6e_$o.log
done
echo "=== v6e vs the shipped v4b build, n=600 (mirror cell)"
uv run python eval_h2h.py --n 600 --artifact build_v6e/submission.tar.gz \
    --opp gbdt:build_v4b/submission.tar.gz > h2h_v6e_vs_v4b.log 2>&1
tail -1 h2h_v6e_vs_v4b.log
echo "=== V6F DONE"
