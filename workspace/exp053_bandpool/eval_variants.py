"""exp053 step 5 -- CRN band eval of the LO-mill deck-ratio variants.

Target: LO-mill's only real bleed is dragapult (0.297). All four variants add
durability the LO pilot ALREADY scores at top priority but the deck doesn't run
(Jumbo Ice Cream 1->4, Hero's Cape 0->1 swapped in as the ACE SPEC), paid for
out of disruption/redundant-switch slots. Same pilot, same shell -- pure
deck-ratio (the exp027 lever).

Gate: band-weighted winrate vs the REAL band pool, CRN-paired (same deals for
every variant), n per matchup from argv. Baseline to beat: stock LO-mill 0.685
(and v016-wall 0.646), both measured under this exact CRN protocol at n=300.

Requirement (not just "dragapult up"): dragapult must rise WITHOUT regressing
the matchups LO already wins -- especially alakazam (0.873) and archaludon
(0.687), which are the whole reason LO beat the wall.

Usage: uv run python eval_variants.py [n]
"""
from __future__ import annotations
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
CRN = os.path.join(WS, "exp052_crn")

sys.path.insert(0, CRN)
from harness_crn import run_gauntlet, load_engine  # noqa: E402
load_engine()

for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp016_pubnb"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from eval_band import build_pool  # noqa: E402
from load_lo import make_lo_agent, lo_deck  # noqa: E402

SEED_BASE = 20260713
VARIANTS = ["stock", "jumbo4", "cape", "both", "maxdur"]


def deck_for(name):
    if name == "stock":
        return lo_deck()
    return json.load(open(os.path.join(HERE, f"lo_v_{name}.json")))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    pool = build_pool()
    print(f"CRN deck-ratio sweep on LO-mill, n={n}/matchup")
    print("baselines under this protocol (n=300): stock LO 0.685, v016-wall 0.646\n")

    rows = {}
    for vname in VARIANTS:
        deck = deck_for(vname)
        agent = make_lo_agent(deck)
        print(f"=== {vname} ===", flush=True)
        tot = 0.0
        row = {}
        for oname, wgt, odeck, ofac in pool:
            t0 = time.time()
            st = run_gauntlet(agent, ofac(odeck), n_games=n, swap_sides=True,
                              crn_seed_base=SEED_BASE + abs(hash(oname)) % 100000)
            wr = st.winrate0
            row[oname] = wr
            tot += wgt * wr
            print(f"  {oname:16} w={wgt:.2f}  wr={wr:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        row["_band_weighted"] = tot
        rows[vname] = row
        print(f"  --> BAND-WEIGHTED = {tot:.4f}\n", flush=True)

    json.dump(rows, open(os.path.join(HERE, f"variants_n{n}.json"), "w"), indent=1)

    base = rows["stock"]
    names = [o[0] for o in pool]
    print(f"{'variant':10} " + " ".join(f"{o[:9]:>9}" for o in names) + f" {'BAND':>8} {'vs stock':>9}")
    for v in VARIANTS:
        r = rows[v]
        d = r["_band_weighted"] - base["_band_weighted"]
        se = math.sqrt(sum((w * math.sqrt(r[o] * (1 - r[o]) / n + base[o] * (1 - base[o]) / n)) ** 2
                           for o, w, _, _ in pool))
        z = d / se if se else 0.0
        flag = "" if v == "stock" else f"{d:+.3f} (z={z:+.2f})"
        print(f"{v:10} " + " ".join(f"{r[o]:9.3f}" for o in names)
              + f" {r['_band_weighted']:8.4f} {flag:>9}")
    print("\n(SE is conservative: it ignores the positive correlation CRN induces)")


if __name__ == "__main__":
    main()
