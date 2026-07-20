"""Can our pool's dedicated dragapult pilot serve as a CANDIDATE at the silver band?
Bar: koff 0.786 (same pool, n=600). Context: new #1 LumenLiquidity runs a Dragapult/
Dusknoir variant; dragapult beats the 28-30% Alakazam lane and is koff's worst matchup.
n=200/matchup CRN screen; escalate only if >= ~0.75."""
import json, os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); WS=os.path.abspath(os.path.join(HERE,".."))
sys.path.insert(0, os.path.join(WS,"exp054_upperband"))
import eval_both_bands as EB
from load_dragapult import make_dragapult_agent
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

n=200
opp=EB.opponents()
wr={}
for oname,w in sorted(EB.SILVER_BAND.items(), key=lambda x:-x[1]):
    deck,fac=opp[oname]
    t0=time.time()
    st=run_gauntlet(make_dragapult_agent(), fac(deck), n_games=n, swap_sides=True,
                    crn_seed_base=EB.SEED+abs(hash("dragcand"+oname))%99991)
    wr[oname]=st.winrate0
    print(f"  {oname:16s} w={w:.3f} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1}) {time.time()-t0:.0f}s", flush=True)
silv=sum(w*wr[o] for o,w in EB.SILVER_BAND.items())/sum(EB.SILVER_BAND.values())
print(f"SILVER-band weighted: {silv:.4f}  (koff bar 0.786)")
