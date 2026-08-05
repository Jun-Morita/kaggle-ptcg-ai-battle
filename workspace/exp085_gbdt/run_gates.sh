#!/usr/bin/env bash
# All gates on the BUILT ARTIFACT via harness.run_gauntlet.
set -u
cd "$(dirname "$0")"
T=build_v3/submission.tar.gz
for o in lucario crustle dragapult archaludon alakazam; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact $T > g_$o.log 2>&1
done
uv run python eval_h2h.py --opp ship --n 200 --artifact $T > g_ship.log 2>&1
uv run python eval_h2h.py --opp ref  --n 200 --artifact $T > g_ref.log 2>&1
for o in lucario crustle dragapult archaludon alakazam ship ref; do printf "%-11s" $o; tail -1 g_$o.log; done
echo "=== GATES DONE"
