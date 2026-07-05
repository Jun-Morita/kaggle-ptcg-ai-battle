"""exp039 eval — guard_opp_policy (v014 turnbeam base + archetype-matched
opponent-reply doom-veto) vs the field, plus PAIRED vs plain v012 and v014 alone.

Usage: MATCH=field|v012|v014 ONLY=<name> uv run python eval_guardopp.py [n]
"""
from __future__ import annotations
import json, os, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp020_deckinnov", "exp022_megastarmie", "exp023_revenge", "exp025_unkoable",
          "exp035_turnbeam", "exp038_beam2ply", "exp039_guardopp"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import guard_opp_policy as GO  # noqa
import revenge_policy as RV  # noqa

V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    os.environ.setdefault("REVENGE_BONUS", "50")
    mode = os.environ.get("MATCH", "field")
    cand = GO.make_agent(V_TREV)
    if mode == "v012":
        field = [("v012_plain", lambda: RV.make_agent(V_TREV))]
    elif mode == "v014":
        import turnbeam_policy as TB
        field = [("v014_beam", lambda: TB.make_agent(V_TREV))]
    else:
        import anti_crustle as AC
        import gust_policy as G
        from load_archaludon import make_archaludon_agent
        import load_dragapult as LD
        field = [("ex_lucario", lambda: AC.make_agent(AC.LUCARIO_DECK)),
                 ("dragapult", LD.make_dragapult_agent),
                 ("archaludon", make_archaludon_agent),
                 ("mirror_chq", lambda: G.make_agent(CH)),
                 ("crustle", AC.make_crustle_agent)]
    only = [s for s in os.environ.get("ONLY", "").split(",") if s]
    if only:
        field = [(nm, mk) for nm, mk in field if nm in only]
    print(f"# guard_opp K={GO.K} mode={mode} n={n}")
    for nm, mk in field:
        t0 = time.time()
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        dt = time.time() - t0
        print(f"  {nm:11s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err={st.errors0} [{dt/max(n,1):.2f}s/g] stats={GO.STATS}", flush=True)


if __name__ == "__main__":
    main()
