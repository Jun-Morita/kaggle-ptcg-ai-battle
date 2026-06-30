for d in charmq v_trev; do
  echo "### $d (n=200) ###"
  env DECK=$d uv run python eval_ratio.py 200 2>/dev/null | grep -E "ex_lucario|dragapult|archaludon|mirror|crustle"
done
echo DONE
