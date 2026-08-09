#!/usr/bin/env bash
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while ! grep -q "BUILD DONE" run_v17.log 2>/dev/null; do sleep 60; done
./run_v18.sh
