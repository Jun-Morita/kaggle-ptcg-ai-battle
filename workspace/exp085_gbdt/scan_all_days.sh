#!/usr/bin/env bash
# Build one teachers index per daily zip. scan_teachers.py always writes to
# exp080_bc/teachers_index.json, so each run is immediately moved aside into
# exp085_gbdt/indices/<date>.json. Idempotent: existing days are skipped.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BC="$HERE/../exp080_bc"
mkdir -p "$HERE/indices"
for z in /home/jun/kaggle-ptcg-ai-battle/references/raw/episodes_*/*.zip; do
  d=$(basename "$z" .zip); d=${d##*-episodes-}
  out="$HERE/indices/$d.json"
  [ -s "$out" ] && { echo "skip $d"; continue; }
  echo "=== $d"
  (cd "$BC" && uv run python scan_teachers.py "$z" >/dev/null 2>&1) || { echo "  FAILED $d"; continue; }
  [ -s "$BC/teachers_index.json" ] && mv "$BC/teachers_index.json" "$out" && \
    python3 -c "
import json,sys,collections
d=json.load(open('$out'))
c=collections.Counter(t[2] for t in d['teachers'])
print('  teachers', len(d['teachers']), 'grimm', c.get('mixed_ex3',0))"
done
