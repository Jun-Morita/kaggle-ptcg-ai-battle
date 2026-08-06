#!/usr/bin/env bash
# v4b = v4 rows, v4 features, bigger trees. Isolates CAPACITY: the corpus and the
# feature set are byte-identical to v4, only num_leaves/lr/min_data change.
set -u
cd "$(dirname "$0")"
echo "=== train";  uv run python train_gbdt.py --rows v4 --rounds 900 --out-tag v4b 2>&1 | grep -v "LightGBM\]"
echo "=== export"; uv run python export_pure.py --tag v4b 2>&1 | tail -8
echo "=== parity"; uv run python parity_pure.py --tag v4b --rows v4 --n 150 2>&1 | tail -4
echo "=== build + smoke"; uv run python build_submission.py --tag v4b --n 25 2>&1 | tail -10
echo "=== gates"
for o in lucario crustle dragapult archaludon; do
  uv run python eval_h2h.py --opp $o --n 200 --artifact build_v4b/submission.tar.gz > gv4b_$o.log 2>&1
done
uv run python eval_h2h.py --opp ship --n 200 --artifact build_v4b/submission.tar.gz > gv4b_ship.log 2>&1
for o in lucario crustle dragapult archaludon ship; do printf "%-11s" $o; tail -1 gv4b_$o.log; done
echo "=== V4B DONE"
