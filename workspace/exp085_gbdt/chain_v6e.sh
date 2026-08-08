#!/usr/bin/env bash
# Wait for the n=800 confirmation to finish before training. Running them
# together would inflate the max_move number the head-to-head reports, and that
# number is a ship gate (the sandbox has 1.6 vCPU and a 600s game budget).
set -u
cd "$(dirname "$0")"
until grep -q "V6D DONE" run_v6d.log 2>/dev/null; do sleep 30; done
exec ./run_v6e.sh
