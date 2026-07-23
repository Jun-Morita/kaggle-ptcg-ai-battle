"""exp075 -- focused MIRROR sweep: which Alakazam list wins the Alakazam mirror?

exp077 established the decision point from real ladder data:

    v025 (pub1034 Alakazam) real winrate 0.621 (108-66) vs koff's 0.558 (82-65)
    every archetype BETTER than koff except one: the Alakazam mirror, 0.333
    the mirror is 21-29% of the field -> it is the whole decision

exp058 already showed the mirror cannot be fixed on the POLICY side (weight
tuning NO-GO at n=300: 0.487/0.513/0.483). So the question is whether it can be
fixed on the DECK side -- the same shape as v012, where a deck-ratio change
worked after a string of policy changes had failed.

Method: hold the PILOT fixed (pub1034 both sides) and vary only our 60 cards
against the stock list. That isolates deck advantage, which is what a deck
decision needs. stock-vs-stock is included as the calibration control and must
land near 0.500.

Candidates:
  stock  : pub1034's own list (control, expect ~0.500)
  E      : the real silver-band list (Enhanced Hammer x4, Dunsparce HP70 x4,
           Enriching Energy, Battle Cage; no Xerosic/Lillie's/NZ) -- this is the
           list that went 6-0 against us on the ladder
  C      : the most common real non-ex Alakazam list from our replay corpus

No CRN pairing (pub1034 samples from Python random), so n=400 -> SE ~0.025.

Usage: uv run python mirror_sweep.py [n]
"""
from __future__ import annotations
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
assert EB.USE_CRN, "CRN harness not active"
import cg as _cg
assert "exp052_crn" in _cg.__file__, f"plain engine: {_cg.__file__}"
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def make_pub(deck=None):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"mir_{_n[0]}", os.path.join(PUB, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(PUB)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if deck is not None:
        mod.read_deck_csv = lambda: list(deck)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 400
    cands = {
        "stock (control)": None,
        "E real-silver":   json.load(open(os.path.join(WS, "exp054_upperband", "real_silver_alakazam.json"))),
        "C most-common":   json.load(open(os.path.join(WS, "exp074_nonex", "real_nonex_deck.json"))),
        "B hammer-hp60":   json.load(open(os.path.join(WS, "exp074_nonex", "real_nonex_worst.json"))),
    }
    print(f"MIRROR sweep vs pub1034 stock, pilot held fixed. n={n}, SE~{(0.25/n)**0.5:.3f}")
    print(f"real-ladder reference: v025 stock scored 0.333 in the live mirror\n")
    print(f"{'our list':18}{'wr vs stock':>13}{'record':>16}   err")
    out = {}
    for name, deck in cands.items():
        st = run_gauntlet(make_pub(deck), make_pub(None), n_games=n, swap_sides=True,
                          crn_seed_base=20260724 + abs(hash(name)) % 99991)
        out[name] = st.winrate0
        print(f"{name:18}{st.winrate0:13.3f}{f'({st.wins0}-{st.wins1}-{st.draws})':>16}   "
              f"({st.errors0},{st.errors1})", flush=True)
    ctrl = out["stock (control)"]
    print(f"\ncontrol landed at {ctrl:.3f} (true value 0.500) -> instrument bias "
          f"{ctrl-0.5:+.3f}; read every row against the control, not against 0.5.")
    json.dump(out, open(os.path.join(HERE, f"mirror_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
