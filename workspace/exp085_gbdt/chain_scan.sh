#!/usr/bin/env bash
# Wait for the last download, then index every new day.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
until grep -q "FETCH2 DONE" fetch2.log 2>/dev/null; do sleep 30; done
exec ./scan_new_days.sh
