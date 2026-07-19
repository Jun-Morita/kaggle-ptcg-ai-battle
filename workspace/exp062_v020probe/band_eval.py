"""exp062 step 1 -- v020 (public archaludon pilot) vs the CURRENT band.

Decision context: Spidops (non-ex aggro) hit 11% share at 0/6 in v029's
850-920 band; contingency asks whether v020 is a viable slot swap. v020's
trade: fixes the TR lane (floor-TR 0.95, exp055) but may bleed the 26%
Alakazam lane. This measures the whole trade at once, n per matchup 200 CRN.

Opponents: EB silver pool (weighted) + tr_spidops (floor, Marshall list)
+ starmie_real (floor) + grimm_froslass (floor).
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
from load_archaludon import make_archaludon_agent
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    opp = EB.opponents()
    extra = {
        "tr_spidops": json.load(open(os.path.join(WS, "exp055_trspidops", "tr_deck.json"))),
        "starmie_real": json.load(open(os.path.join(WS, "exp054_upperband", "starmie_real.json"))),
        "grimm_froslass": json.load(open(os.path.join(WS, "exp061_chipopp", "grimm_froslass.json"))),
    }
    wr = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        t0 = time.time()
        st = run_gauntlet(make_archaludon_agent(), fac(deck), n_games=n, swap_sides=True,
                          crn_seed_base=EB.SEED + abs(hash("v20" + oname)) % 99991)
        wr[oname] = st.winrate0
        print(f"  {oname:16s} w={w:.3f} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1}) {time.time()-t0:.0f}s", flush=True)
    silv = sum(w * wr[o] for o, w in EB.SILVER_BAND.items()) / sum(EB.SILVER_BAND.values())
    print(f"SILVER-band weighted: {silv:.4f}  (koff ref 0.786 same pool n=600)", flush=True)
    for oname, deck in extra.items():
        t0 = time.time()
        st = run_gauntlet(make_archaludon_agent(), EB.RVP.make_agent(deck), n_games=n,
                          swap_sides=True, crn_seed_base=EB.SEED + abs(hash("v20x" + oname)) % 99991)
        print(f"  {oname:16s} (floor) wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1}) {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
