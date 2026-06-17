import sys, os, importlib.util
sys.path.insert(0, os.path.abspath('../exp001_harness'))
sys.path.insert(0, os.path.abspath('../exp002_baselines'))
from harness import load_engine, run_gauntlet
load_engine()
import baselines as B
BUILD=os.path.join(os.path.dirname(__file__),'build')
_c=[0]
def load_sub():
    _c[0]+=1
    spec=importlib.util.spec_from_file_location(f'subv2_{_c[0]}', os.path.join(BUILD,'main.py'))
    m=importlib.util.module_from_spec(spec)
    prev=os.getcwd(); os.chdir(BUILD)
    try: spec.loader.exec_module(m)
    finally: os.chdir(prev)
    return m.agent
deck=B.DECKS['lucario_v2']
# mirror: two independent module instances
a,b=load_sub(),load_sub()
st=run_gauntlet(a,b,n_games=8,swap_sides=True)
print(f'[mirror]     n=8 errors=({st.errors0}+{st.errors1}) winrate0={st.winrate0:.2f} max_move={st.max_move_time0:.1f}s avg_moves={st.total_moves/st.n:.0f}')
# vs dragapult
sub=load_sub()
st2=run_gauntlet(sub, B.make_policy_agent('dragapult'), n_games=8, swap_sides=True)
print(f'[vs dragapult] n=8 winrate={st2.winrate0:.2f} errors=({st2.errors0}+{st2.errors1}) max_move={st2.max_move_time0:.1f}s')
# vs random
sub=load_sub()
st3=run_gauntlet(sub, B.make_random_agent_with_deck(deck,seed=0), n_games=6, swap_sides=True)
print(f'[vs random]   n=6 winrate={st3.winrate0:.2f} errors=({st3.errors0}+{st3.errors1})')
ok = (st.errors0+st.errors1+st2.errors0+st2.errors1+st3.errors0+st3.errors1)==0
print('VERDICT crash-free:', 'PASS' if ok else 'FAIL', '| max_move overall:', max(st.max_move_time0,st2.max_move_time0),'s')
