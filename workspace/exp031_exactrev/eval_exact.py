"""exp031 eval — exact-window revenge (RB env) vs the exp027 field, same protocol.
Usage: REVENGE_BONUS=100 uv run python eval_exact.py [n]"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp020_deckinnov", "exp022_megastarmie", "exp025_unkoable",
          "exp031_exactrev"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import gust_policy as G  # noqa
from load_archaludon import make_archaludon_agent  # noqa
import load_dragapult as LD  # noqa
import exact_policy as X  # noqa

V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    cand = X.make_agent(V_TREV)
    field = [("ex_lucario", lambda: AC.make_agent(AC.LUCARIO_DECK)),
             ("dragapult", LD.make_dragapult_agent),
             ("archaludon", make_archaludon_agent),
             ("mirror_chq", lambda: G.make_agent(CH)),
             ("crustle", AC.make_crustle_agent)]
    print(f"# exact-window RB={X.REVENGE_BONUS} n={n}")
    for nm, mk in field:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        print(f"  {nm:11s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err={st.errors0}", flush=True)


if __name__ == "__main__":
    main()
