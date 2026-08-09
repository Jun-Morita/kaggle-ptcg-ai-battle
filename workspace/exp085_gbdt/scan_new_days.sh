#!/usr/bin/env bash
# Index the days our corpus has never seen. indices/ stops at 2026-07-28; the
# public-notebook sharing deadline was 08-02, so the mix the ladder finishes on
# is entirely outside what we have trained on.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BC="$HERE/../exp080_bc"
mkdir -p "$HERE/indices"
for z in /home/jun/kaggle-ptcg-ai-battle/references/raw/episodes_*/*.zip; do
  d=$(basename "$z" .zip); d=${d##*-episodes-}
  out="$HERE/indices/$d.json"
  [ -s "$out" ] && continue
  echo "=== $d"
  (cd "$BC" && uv run python scan_teachers.py "$z" >/dev/null 2>&1) || { echo "  FAILED $d"; continue; }
  [ -s "$BC/teachers_index.json" ] && mv "$BC/teachers_index.json" "$out" && \
    uv run python -c "
import json,collections
d=json.load(open('$out'))
c=collections.Counter(t[2] for t in d['teachers'])
print('  teachers', len(d['teachers']), '| top:', c.most_common(4))"
done
echo "=== SCAN DONE"; ls "$HERE/indices" | wc -l
