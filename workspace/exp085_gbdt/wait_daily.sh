#!/usr/bin/env bash
# Poll until Kaggle publishes a day's episode dataset, then run daily_cycle.sh.
#
# The episodes for day D show up some hours into D+1, so a fetch that returns
# NOT PUBLISHED YET is normal, not an error. Polls every 20 minutes for 12 hours.
#
#   ./wait_daily.sh 2026-08-14 d0814
#
# No pgrep anywhere: a wait loop that greps for its own script name matches its
# own cmdline and never exits (hit three times in this experiment).
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAY="${1:?usage: wait_daily.sh YYYY-MM-DD TAG}"
TAG="${2:?usage: wait_daily.sh YYYY-MM-DD TAG}"
SHORT="${DAY:5:2}${DAY:8:2}"
RAW=/home/jun/kaggle-ptcg-ai-battle/references/raw

for i in $(seq 1 36); do
  # A previous failed attempt leaves an empty dir behind; the fetch step in
  # daily_cycle.sh treats any *.zip as "already have it", so clear it first.
  [ -d "$RAW/episodes_$SHORT" ] && ! ls "$RAW/episodes_$SHORT"/*.zip >/dev/null 2>&1 \
      && rmdir "$RAW/episodes_$SHORT" 2>/dev/null
  if uv run kaggle datasets files "kaggle/pokemon-tcg-ai-battle-episodes-$DAY" \
       >/dev/null 2>&1; then
    echo "=== published, attempt $i"
    exec ./daily_cycle.sh "$DAY" "$TAG"
  fi
  echo "  [$i] not published yet, sleeping 20m"
  sleep 1200
done
echo "=== gave up after 12h"
