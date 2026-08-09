#!/usr/bin/env bash
# v9 corpus: identical featuriser to v8 (360 columns), 38 days instead of 28.
# The extra 13,098 teacher seats are all 07-30..08-08 -- the meta the ladder is
# actually finishing on. Single variable: data only.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run python build_rows.py --arch mixed_ex3 --exact-deck \
    --max-dec 3000000 --out v9 --index "$PWD/indices/*.json" > build_v9_rows.log 2>&1
echo "=== BUILD DONE"; tail -3 build_v9_rows.log
