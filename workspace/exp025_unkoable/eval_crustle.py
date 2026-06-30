"""Measure v004 Crustle (anti-ex wall) vs the current field incl. Archaludon.

Crustle Safeguard negates Pokemon-ex damage -> should wall Archaludon ex hard.
But it's weak to non-ex / single-prize (they bypass Safeguard). Map the full field.
Usage: uv run python eval_crustle.py [n]
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge", "exp016_pubnb"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
sys.path.insert(0, os.path.dirname(__file__))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
import gust_policy as G  # noqa
from load_archaludon import make_archaludon_agent  # noqa

CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def try_alakazam():
    try:
        import load_alakazam as LA  # noqa
        return LA.make_alakazam_agent()
    except Exception as e:
        return None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    os.environ.setdefault("REVENGE_BONUS", "50")
    crustle = AC.make_crustle_agent()
    field = [("archaludon", make_archaludon_agent),
             ("ex_lucario", lambda: AC.make_agent(AC.LUCARIO_DECK)),
             ("nonex_v011", lambda: G.make_agent(CH)),
             ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    ala = try_alakazam()
    if ala is not None:
        field.append(("alakazam", lambda: ala))
    print(f"# v004 Crustle vs field, n={n}")
    for name, mk in field:
        st = run_gauntlet(crustle, mk(), n_games=n, swap_sides=True)
        print(f"  {name:12s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err_self={st.errors0} err_opp={st.errors1}")


if __name__ == "__main__":
    main()
