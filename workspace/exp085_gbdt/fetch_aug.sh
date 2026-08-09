#!/usr/bin/env bash
# Post-notebook-deadline episode dumps. The public-notebook sharing deadline was
# 2026-08-02, so the archetype mix after that date is the one the ladder finishes
# on -- our indices stop at 07-28 and cannot see it.
set -u
cd /home/jun/kaggle-ptcg-ai-battle/references/raw
for d in 2026-08-03 2026-08-04 2026-08-05 2026-08-06 2026-08-07 2026-08-08; do
  short=${d:5:2}${d:8:2}
  out="episodes_$short"
  [ -s "$out"/*.zip ] 2>/dev/null && { echo "skip $d"; continue; }
  mkdir -p "$out"
  echo "=== $d"
  uv run kaggle datasets download -d "kaggle/pokemon-tcg-ai-battle-episodes-$d" -p "$out" 2>&1 | tail -1
done
echo "=== FETCH DONE"; du -sh episodes_08*
