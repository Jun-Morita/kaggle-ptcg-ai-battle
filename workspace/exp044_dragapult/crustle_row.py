"""Measure OUR crustle wall (v004 lineage, anti_crustle.make_crustle_agent) vs
today's decoded meta: grimmsnarl replica / archaludon / lucario_ex / dragapult /
non-ex (v014 turnbeam) / crustle mirror. n per matchup from argv (default 100)."""
import os, sys, json, time
os.environ.setdefault("REVENGE_BONUS", "50")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp020_deckinnov", "exp022_megastarmie", "exp023_revenge",
          "exp025_unkoable", "exp028_debauchery", "exp029_beliefsearch", "exp035_turnbeam"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet
load_engine()
import anti_crustle as AC
import turnbeam_policy as TB
import load_dragapult as LD
from load_archaludon import make_archaludon_agent
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp023_revenge"))
import revenge_policy as RVP

n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
GRIM = json.load(open(os.path.join(ROOT, "workspace", "exp028_debauchery", "grimmsnarl_deck.json")))

field = [
    ("grimmsnarl",  lambda: RVP.make_agent(list(GRIM))),
    ("archaludon",  make_archaludon_agent),
    ("ex_lucario",  lambda: AC.make_agent(AC.LUCARIO_DECK)),
    ("dragapult",   LD.make_dragapult_agent),
    ("nonex_v014",  lambda: TB.make_agent(V_TREV)),
    ("crustle_mirror", AC.make_crustle_agent),
]
only = [s for s in os.environ.get("ONLY", "").split(",") if s]
if only:
    field = [(nm, mk) for nm, mk in field if nm in only]
total = 0.0
for name, mk in field:
    t0 = time.time()
    st = run_gauntlet(AC.make_crustle_agent(), mk(), n_games=n, swap_sides=True)
    total += st.winrate0
    print(f"  crustle vs {name:016s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
          f"err=({st.errors0},{st.errors1}) [{(time.time()-t0)/n:.2f}s/g]", flush=True)
print(f"TOTAL {total:.3f}")
