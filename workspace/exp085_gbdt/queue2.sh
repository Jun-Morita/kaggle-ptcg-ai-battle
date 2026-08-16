#!/usr/bin/env bash
# field3 after ex4boost. Sequential: concurrent corpora OOM'd the box on 08-15.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
until grep -q "EX4BOOST DONE" run_v51.log 2>/dev/null; do sleep 60; done
echo "=== ex4boost done $(date -u +%H:%M)Z -> field3"
exec ./run_field3.sh
