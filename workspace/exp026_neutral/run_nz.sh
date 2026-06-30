echo "### BASELINE charmq (Legacy Energy) ###"
env DECK=charmq uv run python eval_nz.py 100 2>/dev/null | grep -E "archaludon|ex_lucario|dragapult|mirror|crustle"
echo "### NZ charmq (Neutralization Zone) ###"
env DECK=nz uv run python eval_nz.py 100 2>/dev/null | grep -E "archaludon|ex_lucario|dragapult|mirror|crustle"
echo DONE
