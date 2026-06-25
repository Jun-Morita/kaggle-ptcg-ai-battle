"""Evaluate ONE constant config (set via env) vs the diverse league. Prints JSON.

Run in a fresh subprocess per config (sweep.py) => perfect isolation, no contamination.
Candidate = revenge_policy (reads REVENGE_BONUS/PRIZE_W/BACKUP_CHARGE from env).
League: non-ex mirror (vs v010 gust), ex (lucario_v2), Crustle wall, dragapult spread.
Usage: REVENGE_BONUS=100 uv run python eval_one.py [n]
"""
from __future__ import annotations
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle",
           "exp012_nonex", "exp013_router", "exp018_adaptive", "exp022_megastarmie"):
    sys.path.insert(0, os.path.join(_ROOT, "workspace", _p))

from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
import gust_policy as G  # noqa
import revenge_policy as RV  # noqa: reads env constants at import

DECK = json.load(open(os.path.join(_ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
if isinstance(DECK, dict):
    DECK = DECK.get("charmq") or next(iter(DECK.values()))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    cand = RV.make_agent(DECK)
    league = [
        ("mirror_v010", lambda: G.make_agent(DECK)),   # our weakness; revenge mechanic central
        ("ex",          lambda: AC.make_agent(AC.LUCARIO_DECK)),
        ("crustle",     AC.make_crustle_agent),
        ("dragapult",   lambda: B.make_policy_agent("dragapult")),
    ]
    out = {"config": {"REVENGE_BONUS": RV.REVENGE_BONUS, "PRIZE_W": RV.PRIZE_W,
                      "BACKUP_CHARGE": RV.BACKUP_CHARGE}, "n": n, "matchups": {}}
    for name, mk in league:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        out["matchups"][name] = {"wr": round(st.winrate0, 3), "w": st.wins0, "l": st.wins1,
                                 "d": st.draws, "err_self": st.errors0, "err_opp": st.errors1}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
