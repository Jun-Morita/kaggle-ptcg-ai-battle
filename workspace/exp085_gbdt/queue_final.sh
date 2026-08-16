#!/usr/bin/env bash
# Strictly sequential -- two corpora at once ran the box out of memory on 08-15.
#   ex4boost  counter-strategy on our one agreed-bad matchup; the last lane with
#             a plausible path past the v059 bar
#   narrow2   paired window-slide (low prior: r7/r10 failed at z -6.19 / -2.97)
#   decks2    clone decks, measurement only, first to drop
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
until grep -q "W45 DONE" run_v50.log 2>/dev/null; do sleep 60; done
echo "=== w45 done $(date -u +%H:%M)Z -> ex4boost"
./run_ex4boost.sh
echo "=== ex4boost done $(date -u +%H:%M)Z -> narrow2"
./run_narrow2.sh
echo "=== narrow2 done $(date -u +%H:%M)Z -> decks2"
exec ./run_decks2.sh
