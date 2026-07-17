"""exp059 -- v025 pilot x REAL silver Alakazam list (Hammer x4 variant).

Evidence: exp054-E accidentally measured that (pub pilot + real list) is a
STRONGER agent than (pub pilot + own list) from the LO side (our wr 0.680 vs
0.805). Mechanism: Enhanced Hammer count decides the special-energy war
(Rock Fighting Energy prevents ALL attack effects incl. Powerful Hand).
Pre-registered gates: mirror vs stock >=0.55 @ n=300 CRN; no regression vs
marnie/pure_wall/archaludon/LO(koff) at n=200.

Usage: uv run python gate_hammer4.py [stage: mirror|sides]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp007_anti_crustle", "exp011_meta_watch",
          "exp053_bandpool", "exp054_upperband", "exp057_pubalakazam"):
    sys.path.insert(0, os.path.join(WS, p))

from harness_crn import load_engine, run_gauntlet  # noqa: E402
load_engine()
from load_pub1034 import make_pub1034_agent, pub1034_deck  # noqa: E402
from analyze import card_map  # noqa: E402
import eval_both_bands as EB  # noqa: E402

REAL = json.load(open(os.path.join(WS, "exp054_upperband", "real_silver_alakazam.json")))
SEED = 20260724


def legality(deck):
    byid = card_map()
    assert len(deck) == 60, f"{len(deck)} cards"
    names = Counter(getattr(byid.get(c), "name", str(c)) for c in deck)
    for nm, k in names.items():
        assert k <= 4 or "Basic" in nm, f"{nm} x{k}"
    ace = sum(1 for c in set(deck) if getattr(byid.get(c), "aceSpec", False))
    assert ace <= 1, f"{ace} ACE SPEC"
    print(f"legality OK (ACE SPEC count={ace})")


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "mirror"
    legality(REAL)
    if stage == "mirror":
        st = run_gauntlet(make_pub1034_agent(REAL), make_pub1034_agent(), n_games=300,
                          swap_sides=True, crn_seed_base=SEED)
        print(f"MIRROR real-list vs stock: wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1})  [gate >=0.55]", flush=True)
    else:
        opp = EB.opponents()
        refs = {"marnie": 0.930, "pure_wall": 0.910, "archaludon": 0.865, "crustle_LO": 0.375}
        for oname, ref in refs.items():
            deck, fac = opp[oname]
            st = run_gauntlet(make_pub1034_agent(REAL), fac(deck), n_games=200,
                              swap_sides=True, crn_seed_base=SEED + abs(hash(oname)) % 9999)
            print(f"  vs {oname:11} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  [stock ref {ref}]", flush=True)


if __name__ == "__main__":
    main()
