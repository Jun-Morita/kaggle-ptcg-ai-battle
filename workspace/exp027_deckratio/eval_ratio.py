"""exp027 — deck-ratio optimization: does adding attackers (Trevenant/Cramorant) by
trimming excess draw improve our ex-field winrate without regressing mirror/Crustle?

Pilots a deck variant with v011 (revenge) vs an ex-heavy field. DECK=charmq|v_cram|v_trev|v_both.
Usage: DECK=v_both uv run python eval_ratio.py [n]
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp020_deckinnov", "exp022_megastarmie",
          "exp023_revenge", "exp025_unkoable"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import gust_policy as G  # noqa
from load_archaludon import make_archaludon_agent  # noqa
import load_dragapult as LD  # noqa

CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def load_deck(name):
    if name == "charmq":
        return CH
    return json.load(open(os.path.join(os.path.dirname(__file__), f"{name}.json")))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    os.environ.setdefault("REVENGE_BONUS", "50")
    import revenge_policy as P
    name = os.environ.get("DECK", "charmq")
    cand = P.make_agent(load_deck(name))
    field = [("ex_lucario", lambda: AC.make_agent(AC.LUCARIO_DECK)),
             ("dragapult", LD.make_dragapult_agent),
             ("archaludon", make_archaludon_agent),
             ("mirror", lambda: G.make_agent(CH)),
             ("crustle", AC.make_crustle_agent)]
    print(f"# DECK={name} policy=v011revenge n={n}")
    for nm, mk in field:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        print(f"  {nm:11s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err_self={st.errors0}")


if __name__ == "__main__":
    main()
