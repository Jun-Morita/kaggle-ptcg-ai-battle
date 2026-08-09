#!/usr/bin/env bash
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "TRAIN DONE" chain_v9.log 2>/dev/null; do sleep 60; done
./run_v19.sh
