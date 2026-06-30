"""exp026 — does Neutralization Zone (anti-ex ACE SPEC) help our non-ex deck?

Swaps Legacy Energy(12)->Neutralization Zone(1247). NZ prevents ALL ex/V attack damage
to non-Rule-Box Pokemon -> our all-non-ex board is immune to ex attacks (Archaludon ex
Metal Defender 220, Dragapult ex, Mega Lucario ex). Policy unchanged (v011 revenge); the
engine applies NZ automatically once the stadium is in play (scored 10000 default -> played).
Usage: DECK=charmq|nz uv run python eval_nz.py [n]
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge", "exp025_unkoable"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
import gust_policy as G  # noqa
from load_archaludon import make_archaludon_agent  # noqa

CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH
NZ = json.load(open(os.path.join(os.path.dirname(__file__), "charmq_nz_deck.json")))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    os.environ.setdefault("REVENGE_BONUS", "50")
    import revenge_policy as P
    deck = NZ if os.environ.get("DECK", "charmq") == "nz" else CH
    cand = P.make_agent(deck)
    league = [("archaludon", make_archaludon_agent),
              ("ex_lucario", lambda: AC.make_agent(AC.LUCARIO_DECK)),
              ("dragapult", lambda: B.make_policy_agent("dragapult")),
              ("mirror_v010", lambda: G.make_agent(CH)),
              ("crustle", AC.make_crustle_agent)]
    print(f"# deck={os.environ.get('DECK','charmq')} policy=revenge n={n}")
    for name, mk in league:
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        print(f"  {name:12s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err_self={st.errors0} err_opp={st.errors1}")


if __name__ == "__main__":
    main()
