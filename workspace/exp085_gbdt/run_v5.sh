#!/usr/bin/env bash
# v5 = v4b capacity (511 leaves) + 8 ability/attachment precondition features.
# Same corpus size, same hyperparameters as v4b, so the delta is the FEATURES.
set -eu
cd "$(dirname "$0")"
echo "=== train";  uv run python train_gbdt.py --rows v5 --rounds 900 2>&1 | grep -v "LightGBM\]"
echo "=== export"; uv run python export_pure.py --tag v5 2>&1 | tail -8
echo "=== parity"; uv run python parity_pure.py --tag v5 --rows v5 --n 150 2>&1 | tail -4
echo "=== build + smoke"; uv run python build_submission.py --tag v5 --n 25 2>&1 | tail -10
echo "=== gates"
for o in lucario crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact build_v5/submission.tar.gz > gv5_$o.log 2>&1
done
uv run python eval_h2h.py --opp ship --n 200 --artifact build_v5/submission.tar.gz > gv5_ship.log 2>&1
for o in lucario crustle dragapult archaludon ship; do printf "%-11s" $o; tail -1 gv5_$o.log; done
echo "=== V5 DONE"
