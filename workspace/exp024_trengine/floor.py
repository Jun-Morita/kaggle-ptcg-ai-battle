"""Measure how our current best policy pilots a given deck (the TR-engine brick test).

Usage: POLICY=revenge|gust DECK=yushin|charmq uv run python floor.py [n]
Compares: candidate deck+policy vs the standard league (mirror v010, ex, Crustle, dragapult).
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
import gust_policy as G  # noqa

DECKS = {
    "yushin": os.path.join(os.path.dirname(__file__), "yushin_deck.json"),
    "charmq": os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json"),
}


def load_deck(name):
    d = json.load(open(DECKS[name]))
    return d.get("charmq") if isinstance(d, dict) else d


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    which = os.environ.get("POLICY", "revenge")
    deckname = os.environ.get("DECK", "yushin")
    deck = load_deck(deckname)
    if which == "revenge":
        os.environ.setdefault("REVENGE_BONUS", "50")
        import revenge_policy as P
        cand = P.make_agent(deck)
    elif which == "tr":
        import tr_policy as P
        cand = P.make_agent(deck)
    else:
        cand = G.make_agent(deck)
    charmq = load_deck("charmq")
    league = [("mirror_v010", lambda: G.make_agent(charmq)),
              ("ex", lambda: AC.make_agent(AC.LUCARIO_DECK)),
              ("crustle", AC.make_crustle_agent),
              ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    print(f"# deck={deckname} policy={which} n={n}")
    for name, mk in league:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        print(f"  {name:12s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err_self={st.errors0}")


if __name__ == "__main__":
    main()
