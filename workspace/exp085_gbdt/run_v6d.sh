#!/usr/bin/env bash
# Confirm v6 at a sample size that can actually decide a ship, plus the field
# regression check. The n=300 result (0.537, z +1.27) is not enough on its own:
# exp085 has already seen a 300-game ordering reverse at 400.
set -u
cd "$(dirname "$0")"
echo "=== v6 vs the shipped v4b build (v053), n=800"
uv run python eval_h2h.py --n 800 --artifact build_v6/submission.tar.gz \
    --opp gbdt:build_v4b/submission.tar.gz > h2h_v6_vs_v4b_n800.log 2>&1
tail -1 h2h_v6_vs_v4b_n800.log
echo "=== field regression, n=200 each"
for o in lucario crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact build_v6/submission.tar.gz > gv6_$o.log 2>&1
  printf "%-11s" $o; tail -1 gv6_$o.log
done
echo "=== V6D DONE"
