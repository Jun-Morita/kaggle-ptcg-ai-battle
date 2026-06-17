"""Realistic-belief eval: assume opponent deck = lucario_v2 (meta default, NOT oracle).
Conservative Override margin=0.10. This is the true submission condition."""
import sys, os, time, json
sys.path.insert(0, os.path.abspath('../exp001_harness'))
sys.path.insert(0, os.path.abspath('../exp002_baselines'))
from harness import run_gauntlet
from agent_pimc import make_pimc_agent
import baselines as B
deck=B.DECKS['lucario_v2']
BELIEF=deck  # fixed belief: assume opponent is Lucario (saturated ladder)
opps={'random':B.make_random_agent_with_deck(deck,seed=0),
      'dragapult':B.make_policy_agent('dragapult'),
      'lucario_v1':B.make_policy_agent('lucario_v1'),
      'lucario_v2':B.make_policy_agent('lucario_v2')}
n=12; res={}; wrs=[]
for name,opp in opps.items():
    pimc=make_pimc_agent(deck, opp_deck=BELIEF, k_rollouts=6, max_candidates=4, horizon=40, seed=1, use_belief=True, margin=0.10)
    t0=time.perf_counter(); st=run_gauntlet(pimc,opp,n_games=n,swap_sides=True); dt=time.perf_counter()-t0
    res[name]={'winrate':round(st.winrate0,3),'rec':f'{st.wins0}-{st.wins1}','max_move_s':round(st.max_move_time0,1),'spg':round(dt/n,1)}
    if name!='random': wrs.append(st.winrate0)
    print(f'vs {name:11s} winrate={st.winrate0:.3f} ({st.wins0}-{st.wins1}) max_move={st.max_move_time0:.1f}s {dt/n:.1f}s/game',flush=True)
avg=round(sum(wrs)/len(wrs),3)
print(f'\navg vs rule-based = {avg:.3f} (bar 0.680) [realistic belief=lucario_v2 fixed, margin=0.10]')
json.dump({'belief':'lucario_v2_fixed','margin':0.10,'n':n,'results':res,'avg_vs_rulebased':avg}, open('results/pimc_realistic.json','w'), indent=2)
