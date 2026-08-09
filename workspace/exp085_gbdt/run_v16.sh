#!/usr/bin/env bash
# The two mirror measurements disagree about v8:
#   vs the tetsutani reference (n=1000)   v8 0.531  >  v054 0.512
#   vs the v054 build directly (n=800)    v8 0.480  <  v054
# Both are "the mirror", both are inside noise, and they point opposite ways.
# n=1600 on the direct match, and the reference match repeated for v054 so the
# two builds are measured on the same day under the same load.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== v8 vs the v054 build, n=1600"
uv run python eval_h2h.py --n 1600 --artifact build_v8/submission.tar.gz \
    --opp gbdt:build_v6/submission.tar.gz > h2h_v8_vs_v6_n1600.log 2>&1
tail -1 h2h_v8_vs_v6_n1600.log
echo "=== v054 build vs reference, n=1000 (repeat)"
uv run python eval_h2h.py --opp ref --n 1000 \
    --artifact build_v6/submission.tar.gz > mir_v6_rep.log 2>&1
tail -1 mir_v6_rep.log
echo "=== V16 DONE"
