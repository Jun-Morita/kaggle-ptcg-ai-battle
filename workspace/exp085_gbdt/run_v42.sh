#!/usr/bin/env bash
# 08-13 added. Two questions, in this order.
#
#   1. Did the meta move? The gate weights come from the observed field, and the
#      field has been rotating hard (mixed_ex3 63.3% on 08-01 -> 14.1% on 08-12,
#      dragapult 4.0% -> 25.8%). If the mix moved 5pp the gate totals get
#      recomputed -- that costs a minute and no re-measurement.
#   2. Does the extra day help? Four extensions in a row said no (12d 0.6640 ->
#      16d 0.6480, monotone), and the reason is known: the strong Grimmsnarl
#      teachers per day fell from ~270 to ~32. Measuring anyway, because the
#      whole point of the daily loop is to notice the day that breaks the trend.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
./scan_new_days.sh 2>&1 | tail -3
echo "=== deck distribution, 08-08 onward"
uv run python - <<'PY'
import glob, json
from collections import Counter
rows = []
for p in sorted(glob.glob("indices/2026-*.json")):
    day = p[-15:-5]
    if day < "2026-08-08":
        continue
    d = json.load(open(p))
    c = Counter(t[2] for t in d["teachers"])
    rows.append((day, sum(c.values()), c))
order = sorted({a for _, _, c in rows for a in c},
               key=lambda a: -sum(c[a] for _, _, c in rows))[:7]
print(f"{'day':<12}{'teachers':>9}" + "".join(f"{a[:11]:>12}" for a in order))
for day, tot, c in rows:
    print(f"{day:<12}{tot:>9}" + "".join(f"{c[a]/tot:>11.1%}" for a in order))
PY
exec ./daily_cycle.sh 2026-08-13 d0813
