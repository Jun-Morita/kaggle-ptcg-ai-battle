"""exp057 -- (1) v023 vs pub1034 n=200 CRN; (2) pub1034 as CANDIDATE on both bands."""
from __future__ import annotations
import importlib.util, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn","exp001_harness","exp053_bandpool","exp054_upperband","exp057_pubalakazam"):
    sys.path.insert(0, os.path.join(WS, p))
from harness_crn import load_engine, run_gauntlet
load_engine()
from load_pub1034 import make_pub1034_agent
import eval_both_bands as EB
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")

def make_koff():
    spec = importlib.util.spec_from_file_location("lo_y", os.path.join(LO_DIR,"main.py"))
    mod = importlib.util.module_from_spec(spec); prev=os.getcwd()
    try: os.chdir(LO_DIR); spec.loader.exec_module(mod)
    finally: os.chdir(prev)
    mod.should_ko_mode = lambda *a,**k: False
    deck = json.load(open(os.path.join(WS,"exp054_upperband","lo_deck.json")))
    def agent(obs):
        if obs.get("select") is None: return list(deck)
        return mod.agent(obs)
    return agent

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    st = run_gauntlet(make_koff(), make_pub1034_agent(), n_games=n, swap_sides=True, crn_seed_base=20260722)
    print(f"[1] v023-koff vs pub1034: wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1})  (live alakazam ref 0.48)", flush=True)

    opp = EB.opponents()
    needed = sorted(set(EB.OUR_BAND) | set(EB.SILVER_BAND))
    wr = {}
    print(f"[2] pub1034 as candidate, n={n}/matchup, CRN", flush=True)
    for oname in needed:
        deck, fac = opp[oname]
        t0 = time.time()
        st = run_gauntlet(make_pub1034_agent(), fac(deck), n_games=n, swap_sides=True,
                          crn_seed_base=EB.SEED + abs(hash(oname)) % 99991)
        wr[oname] = st.winrate0
        print(f"  {oname:14} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1}) {time.time()-t0:.0f}s", flush=True)
    ours = sum(w * wr[o] for o, w in EB.OUR_BAND.items())
    silv = sum(w * wr[o] for o, w in EB.SILVER_BAND.items()) / sum(EB.SILVER_BAND.values())
    print(f"pub1034: OUR band {ours:.4f} | SILVER band {silv:.4f}  (v023 ref: 0.648 / 0.792)")
    json.dump({"wr": wr, "our": ours, "silver": silv}, open(os.path.join(HERE, f"pub1034_n{n}.json"), "w"))

if __name__ == "__main__":
    main()
