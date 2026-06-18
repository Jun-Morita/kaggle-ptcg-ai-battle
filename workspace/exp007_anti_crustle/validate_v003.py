import sys, os, importlib.util
sys.path.insert(0, os.path.abspath('../exp001_harness'))
sys.path.insert(0, os.path.abspath('../exp002_baselines'))
from harness import load_engine, run_gauntlet
load_engine()
import anti_crustle as AC
import baselines as B
BUILD=os.path.join(os.path.dirname(__file__),'build'); _c=[0]
def load_sub():
    _c[0]+=1
    spec=importlib.util.spec_from_file_location(f'v3_{_c[0]}',os.path.join(BUILD,'main.py')); m=importlib.util.module_from_spec(spec)
    prev=os.getcwd(); os.chdir(BUILD)
    try: spec.loader.exec_module(m)
    finally: os.chdir(prev)
    return m.agent
deck=AC.LUCARIO_DECK
a,b=load_sub(),load_sub()
st=run_gauntlet(a,b,n_games=10,swap_sides=True)
print(f'[mirror]   n=10 errors=({st.errors0}+{st.errors1}) wr0={st.winrate0:.2f} max_move={st.max_move_time0:.2f}s')
sub=load_sub(); st2=run_gauntlet(sub,AC.make_crustle_agent(),n_games=20,swap_sides=True)
print(f'[vs crustle] n=20 winrate={st2.winrate0:.2f} errors=({st2.errors0}+{st2.errors1})')
sub=load_sub(); st3=run_gauntlet(sub,B.make_random_agent_with_deck(deck,seed=0),n_games=8,swap_sides=True)
print(f'[vs random]  n=8 winrate={st3.winrate0:.2f} errors=({st3.errors0}+{st3.errors1})')
tot=st.errors0+st.errors1+st2.errors0+st2.errors1+st3.errors0+st3.errors1
print('VERDICT crash-free:','PASS' if tot==0 else 'FAIL','| max_move:',round(max(st.max_move_time0,st2.max_move_time0,st3.max_move_time0),3),'s')
