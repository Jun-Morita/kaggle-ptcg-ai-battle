"""exp037 — sweep turn-beam's search budget (TB_K/TB_BEAM/TB_BRANCH/TB_MAXSTEPS).
v014 uses <1% of the 600s/game time pool; this tests whether widening the beam
(more candidate lines explored, deeper) buys more throughput-verified overrides
without changing the mechanism. Uses exp035's turnbeam_policy.py directly via env.

Usage: TB_BEAM=10 TB_BRANCH=16 TB_MAXSTEPS=3000 TB_K=2 uv run python eval_config.py [n] [tag]
"""
from __future__ import annotations
import json, os, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp020_deckinnov", "exp022_megastarmie", "exp023_revenge", "exp025_unkoable",
          "exp035_turnbeam"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import turnbeam_policy as TB  # noqa
import revenge_policy as RV  # noqa

V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
CH = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
CH = CH.get("charmq") if isinstance(CH, dict) else CH


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    tag = sys.argv[2] if len(sys.argv) > 2 else "cfg"
    os.environ.setdefault("REVENGE_BONUS", "50")
    cand = TB.make_agent(V_TREV)
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
    print(f"# [{tag}] K={TB.K} beam={TB.BEAM} branch={TB.BRANCH} maxsteps={TB.MAXSTEPS} n={n}")
    for nm, mk in field:
        t0 = time.time()
        st = run_gauntlet(cand, mk(), n_games=n, swap_sides=True)
        dt = time.time() - t0
        print(f"  {nm:11s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err={st.errors0} [{dt/max(n,1):.2f}s/g] fired={TB.STATS['fired']}/{TB.STATS['planned']}", flush=True)


if __name__ == "__main__":
    main()
