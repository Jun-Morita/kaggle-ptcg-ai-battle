"""Adoption gate screen for the public "[STRONG START] Baseline Agent V10 | LB 950+"
notebook (romanrozen, copied from aristophanivan/improved-probabilistic-agent):
Mega Lucario ex + search-augmented expectimax, deck AND pilot shipped together.

Bar: koff silver-band weighted 0.786 (same pool). n=200/matchup CRN screen;
escalate to n=600 only if >= ~0.75.

Prior evidence AGAINST (recorded before running, to avoid post-hoc rationalising):
  - author's own ladder standing is rank 4078 / 506.1 (title claim "LB 950+" unbacked)
  - Mega Lucario band share falls with altitude: 6.7% (900-999) -> 3.0% -> 0% (1100+)
This screen exists because our standard is measurement, not inference.
"""
import os, sys, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
AGENT_DIR = os.path.join(HERE, "agent")

sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

_n = [0]


def make_cand():
    """Bare-exec the candidate's own main.py (its pilot ships with the deck)."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"megaluc{_n[0]}", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    opp = EB.opponents()
    wr = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        t0 = time.time()
        st = run_gauntlet(make_cand(), fac(deck), n_games=n, swap_sides=True,
                          crn_seed_base=EB.SEED + abs(hash("megaluc" + oname)) % 99991)
        wr[oname] = st.winrate0
        print(f"  {oname:16s} w={w:.3f} wr={st.winrate0:.3f} "
              f"({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1}) "
              f"{time.time()-t0:.0f}s", flush=True)
    silv = sum(w * wr[o] for o, w in EB.SILVER_BAND.items()) / sum(EB.SILVER_BAND.values())
    print(f"SILVER-band weighted: {silv:.4f}  (koff bar 0.786)")


if __name__ == "__main__":
    main()
