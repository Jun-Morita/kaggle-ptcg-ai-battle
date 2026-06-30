for pol in revenge unkoable; do
  echo "### $pol ###"
  env POLICY=$pol uv run python eval_arch.py 150 2>/dev/null | grep -E "archaludon|mirror|ex|crustle"
done
echo DONE
