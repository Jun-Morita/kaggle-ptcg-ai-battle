"""Eval a policy (charmq deck) vs Archaludon + the league. POLICY=revenge|unkoable.

Usage: POLICY=revenge uv run python eval_arch.py [n]
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
sys.path.insert(0, os.path.dirname(__file__))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import gust_policy as G  # noqa
from load_archaludon import make_archaludon_agent  # noqa

CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    which = os.environ.get("POLICY", "revenge")
    os.environ.setdefault("REVENGE_BONUS", "50")
    if which == "unkoable":
        import unkoable_policy as P
    else:
        import revenge_policy as P
    cand = P.make_agent(CH)
    league = [("archaludon", make_archaludon_agent),
              ("mirror_v010", lambda: G.make_agent(CH)),
              ("ex", lambda: AC.make_agent(AC.LUCARIO_DECK)),
              ("crustle", AC.make_crustle_agent)]
    print(f"# deck=charmq policy={which} n={n}")
    for name, mk in league:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        print(f"  {name:12s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err_self={st.errors0} err_opp={st.errors1}")


if __name__ == "__main__":
    main()
