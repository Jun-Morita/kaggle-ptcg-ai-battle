#!/usr/bin/env bash
# Does CRN actually shrink the spread on THIS pairing? exp052 measured 4.66x on
# a different pair of builds, so it has to be re-checked here before the number
# is trusted. Eight repeats each way at n=200: the observed standard deviation
# across repeats is the thing that matters, not any single winrate.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== CRN OFF"
uv run python eval_crn.py --a build_v8 --b build_v6 --n 200 --repeats 8 --nocrn 2>&1 | tail -12
echo "=== CRN ON"
uv run python eval_crn.py --a build_v8 --b build_v6 --n 200 --repeats 8 2>&1 | tail -12
echo "=== CRN VALIDATION DONE"
