for d in charmq v_cram v_trev v_both; do
  echo "### $d ###"
  env DECK=$d uv run python eval_ratio.py 80 2>/dev/null | grep -E "ex_lucario|dragapult|archaludon|mirror|crustle"
done
echo DONE
