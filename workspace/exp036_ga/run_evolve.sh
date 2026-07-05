#!/bin/bash
cd "$(dirname "$0")"
export REVENGE_BONUS=50 PYTHONUNBUFFERED=1
# resume loop: survive worker crashes; evolve.py resumes from gens/ automatically
until uv run python evolve.py 40 >> evolve.log 2>&1; do
  echo "=== evolve crashed, resuming ===" >> evolve.log
  sleep 5
done
touch EVOLVE_DONE
