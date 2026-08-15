"""Full leaderboard snapshot: our rank + the 5% silver cut.

The SDK prints the next page token to stdout instead of returning it, so we
capture stdout per page and re-feed the token.
"""
import contextlib
import csv
import io
import re
import sys

from kaggle.api.kaggle_api_extended import KaggleApi

OUT = sys.argv[1] if len(sys.argv) > 1 else "lb_full.csv"

api = KaggleApi()
api.authenticate()

rows = []
tok = None
for _ in range(80):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        page = api.competition_leaderboard_view(
            "pokemon-tcg-ai-battle", page_size=200, page_token=tok
        )
    m = re.search(r"Next Page Token = (\S+)", buf.getvalue())
    if not page:
        break
    rows += page
    if not m:
        break
    tok = m.group(1)

with open(OUT, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["rank", "team", "score"])
    for i, x in enumerate(rows, 1):
        w.writerow([i, getattr(x, "team_name", "") or "", x.score])

n = len(rows)
cut = int(n * 0.05)
lines = [f"teams {n}   5% cut = rank {cut} @ {rows[cut - 1].score}"]
for i, x in enumerate(rows, 1):
    if "Morita" in (getattr(x, "team_name", "") or ""):
        margin = float(x.score) - float(rows[cut - 1].score)
        lines.append(f"us rank {i} @ {x.score}   margin {margin:+.1f}")
lines.append("top5 " + " ".join(f"{i + 1}:{rows[i].score}" for i in range(5)))
sys.stderr.write("\n".join(lines) + "\n")
