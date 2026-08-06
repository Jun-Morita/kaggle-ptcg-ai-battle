#!/usr/bin/env bash
# v4 (318 features) end to end, then the value model. One change measured at a time:
# this run isolates the FEATURES; search is gated separately afterwards.
set -u
cd "$(dirname "$0")"
echo "=== train ranker";  uv run python train_gbdt.py --rows v4 --rounds 600 2>&1 | grep -v "LightGBM\]"
echo "=== export";        uv run python export_pure.py --tag v4 2>&1 | tail -8
echo "=== parity";        uv run python parity_pure.py --tag v4 --n 150 2>&1 | tail -4
echo "=== build + smoke"; uv run python build_submission.py --tag v4 --n 25 2>&1 | tail -10
echo "=== gates (built artifact, run_gauntlet)"
for o in lucario crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact build_v4/submission.tar.gz > gv4_$o.log 2>&1
done
uv run python eval_h2h.py --opp ship --n 200 --artifact build_v4/submission.tar.gz > gv4_ship.log 2>&1
for o in lucario crustle dragapult archaludon ship; do printf "%-11s" $o; tail -1 gv4_$o.log; done
echo "=== value model"
uv run python train_value.py --rows v1 --rounds 500 2>&1 | grep -v "LightGBM\]"
echo "=== V4 DONE"
