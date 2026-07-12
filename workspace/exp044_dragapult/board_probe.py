"""Play n games (turnbeam chain vs local dragapult baseline) and log, at each of
our attack-capable turns: opp board composition + whether a KO-able Dreepy/Drakloak
gust existed + what we actually targeted."""
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
            if o.select is not None and int(o.select.context) == 0 and int(o.select.type) == 0:
                cur = o.current
                me = cur.players[cur.yourIndex]
                opp = cur.players[1 - cur.yourIndex]
                bench_ids = [p.id for p in (opp.bench or []) if p]
                act_id = opp.active[0].id if opp.active else None
                stats["turnsel"] += 1
                n_line = sum(1 for i in bench_ids if i in (119, 120))
                if n_line: stats["line_on_bench"] += 1
                stats[f"oppact_{NM.get(act_id, act_id)}"] += 1
        except Exception:
            pass
        return out
    return a

base = TB.make_agent(V_TREV)
st = run_gauntlet(wrap(base), LD.make_dragapult_agent(), n_games=30, swap_sides=True)
print("wr", st.winrate0, st.wins0, st.wins1, "err", st.errors0)
for k, v in sorted(stats.items(), key=lambda x: -x[1]):
    print(f"  {k:40s} {v}")
