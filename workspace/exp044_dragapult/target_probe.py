"""Log our ATTACK-target distribution vs local dragapult, flag off/on."""
import os, sys, json
from collections import Counter
os.environ.setdefault("REVENGE_BONUS", "50")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp020_deckinnov", "exp022_megastarmie", "exp023_revenge",
          "exp025_unkoable", "exp029_beliefsearch", "exp035_turnbeam"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet
load_engine()
import turnbeam_policy as TB
import load_dragapult as LD
from cg import api

V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
NM = {c.cardId: c.name for c in api.all_card_data()}
stats = Counter()

def wrap(agent):
    def a(obs_dict):
        out = agent(obs_dict)
        try:
            o = api.to_observation_class(obs_dict)
            sel = o.select
            if sel is not None and int(sel.context) == 0 and int(sel.type) == 0:
                cur = o.current
                opp = cur.players[1 - cur.yourIndex]
                for i in out:
                    if 0 <= i < len(sel.option):
                        op = sel.option[i]
                        if int(op.type) == 7:  # ATTACK: defender = current opp active
                            tid = opp.active[0].id if opp.active else None
                            stats[f"atk_into_{NM.get(tid, tid)}"] += 1
                        elif int(op.type) == 8 and int(op.inPlayArea) == 5 and getattr(op, 'playerIndex', 0) != cur.yourIndex:
                            pass
        except Exception:
            pass
        return out
    return a

flag = os.environ.get("DRAG_SNIPE", "0")
base = TB.make_agent(V_TREV)
st = run_gauntlet(wrap(base), LD.make_dragapult_agent(), n_games=40, swap_sides=True)
print(f"DRAG_SNIPE={flag} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err={st.errors0}")
for k, v in sorted(stats.items(), key=lambda x: -x[1]):
    print(f"  {k:36s} {v}")
