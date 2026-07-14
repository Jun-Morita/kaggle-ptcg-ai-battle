"""exp055 -- TR Spidops feasibility spike, stage 1: FLOOR pilots.

Hypothesis (1 exp, 1 hypothesis): TR's edge over the Safeguard metagame
(wall + LO) is DECK-STRUCTURAL (non-ex attackers bypass Safeguard/Zone), so
even a generic floor pilot should show it. Gate: >=0.6 vs pure_wall AND vs
LO(koff), while not collapsing (<0.45) vs alakazam/archaludon.
Known risk: the TR supporter engine bricked our generic pilots before
(Debauchery mimic 0.167, exp013).

Usage: uv run python floor_test.py [n]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp007_anti_crustle", "exp023_revenge",
          "exp025_unkoable", "exp020_deckinnov", "exp053_bandpool", "exp054_upperband"):
    sys.path.insert(0, os.path.join(WS, p))

from harness_crn import load_engine, run_gauntlet  # noqa: E402
load_engine()
import anti_crustle as AC  # noqa: E402
import revenge_policy as RVP  # noqa: E402
from load_lo import lo_deck  # noqa: E402
import eval_both_bands as EB  # noqa: E402

SEED = 20260719
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
_n = [0]


def make_lo_koff(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_o{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.should_ko_mode = lambda *a, **k: False

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    tr = json.load(open(os.path.join(HERE, "tr_deck.json")))
    opp = EB.opponents()
    targets = {
        "pure_wall": lambda: AC.make_crustle_agent(),
        "LO_koff": lambda: make_lo_koff(lo_deck()),
        "alakazam": lambda: RVP.make_agent(opp["alakazam"][0]),
        "archaludon": lambda: opp["archaludon"][1](None),
    }
    pilots = {
        "generic(AC)": lambda: AC.make_agent(list(tr)),
        "revenge(RVP)": lambda: RVP.make_agent(list(tr)),
    }
    print(f"TR Spidops floor test, n={n}/cell, CRN shared seeds")
    print("(reference: real TR at our altitude beat v023-LO 3-0 and Budew-wall 3-0)\n")
    for pname, pfac in pilots.items():
        print(f"=== pilot: {pname} ===", flush=True)
        for oname, ofac in targets.items():
            st = run_gauntlet(pfac(), ofac(), n_games=n, swap_sides=True,
                              crn_seed_base=SEED + abs(hash(oname)) % 9999)
            print(f"  vs {oname:11} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})", flush=True)


if __name__ == "__main__":
    main()
