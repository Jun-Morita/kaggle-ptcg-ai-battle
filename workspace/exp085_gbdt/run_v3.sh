#!/usr/bin/env bash
# v3: exact-deck corpus -> train -> export -> parity -> smoke -> head-to-head.
# Every gate here runs on harness.run_gauntlet, the path all shipped builds used.
set -u
cd "$(dirname "$0")"
echo "=== train";  uv run python train_gbdt.py --rows v3 --rounds 600 2>&1 | grep -v "LightGBM\]"
echo "=== export"; uv run python export_pure.py --tag v3 2>&1 | tail -8
echo "=== parity"; uv run python parity_pure.py --tag v3 --n 150 2>&1 | tail -4
echo "=== build + smoke (extracted artifact, exec without __file__)"
uv run python build_submission.py --tag v3 --n 25 2>&1 | tail -10
echo "=== head-to-head on run_gauntlet"
for o in lucario crustle dragapult; do
  uv run python eval_h2h.py --opp $o --n 120 --pure results/gbdt_pure_v3.pkl > h2h2_$o.log 2>&1
done
uv run python eval_h2h.py --opp ship --n 160 --pure results/gbdt_pure_v3.pkl > h2h2_ship.log 2>&1
for o in lucario crustle dragapult ship; do printf "%-11s" $o; tail -1 h2h2_$o.log; done
echo "=== ALL DONE"
