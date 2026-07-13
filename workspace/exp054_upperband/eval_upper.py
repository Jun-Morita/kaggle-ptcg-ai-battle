"""exp054 -- measure our candidates against the SILVER-BAND pool (not our own).

exp053's calibrated Elo model said: being better in OUR band (700-770) cannot
reach silver, because climbing changes who you face. extract_upper.py then
showed the silver band (sampled from tomatomato's 719 replays at LB 948.8, i.e.
right on the 933 boundary) is a different world:

                        our band     silver band
    Alakazam family       ~18%          40.6%    <- biggest bloc
    Archaludon (ex4)        9%          26.4%    <- the wall up there
                                                    (tomatomato goes 0.25 into it)
    Marnie/Munkidori       n/a          11.1%
    lucario_ex             31%           9.5%
    crustle/LO             20%           3.3%

Our own measured matchup winrates say v016-wall (alakazam 0.240, archaludon
0.170) would be CRUSHED up there, while LO-mill (alakazam 0.910, archaludon
0.693) is the only candidate structurally suited to it. This script measures
that properly instead of extrapolating.

Pilot convention matches exp053's eval_band.py so numbers stay comparable:
dedicated public pilots where we have them (Archaludon / dragapult / LO), the
generic revenge policy otherwise.

Usage: uv run python eval_upper.py [n] [--crn]
"""
from __future__ import annotations
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
CRN = os.path.join(WS, "exp052_crn")

USE_CRN = "--crn" in sys.argv
if USE_CRN:
    sys.path.insert(0, CRN)
    from harness_crn import run_gauntlet, load_engine  # noqa: E402
    load_engine()
else:
    sys.path.insert(0, os.path.join(WS, "exp001_harness"))
    from harness import run_gauntlet, load_engine  # noqa: E402
    load_engine()

for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp007_anti_crustle"),
          os.path.join(WS, "exp020_deckinnov"), os.path.join(WS, "exp025_unkoable"),
          os.path.join(WS, "exp023_revenge"), os.path.join(WS, "exp053_bandpool")):
    if p not in sys.path:
        sys.path.insert(0, p)

import anti_crustle as AC  # noqa: E402
import revenge_policy as RVP  # noqa: E402
from load_dragapult import make_dragapult_agent  # noqa: E402
from load_archaludon import make_archaludon_agent  # noqa: E402
from load_lo import make_lo_agent, lo_deck  # noqa: E402
from eval_band import load_built  # noqa: E402

SEED_BASE = 20260714


def up(name):
    return json.load(open(os.path.join(HERE, f"up_{name}.json")))


def build_upper_pool():
    """(name, share, deck, factory). Shares from extract_upper.py (renormalized
    over the 96.6% these 7 cover)."""
    raw = [
        ("alakazam_dunsp", 0.285, up("non_ex_attackers"), lambda d: RVP.make_agent(d)),
        ("archaludon", 0.264, up("mixed_ex4"), lambda d: make_archaludon_agent()),
        ("alakazam", 0.121, up("mixed_ex1"), lambda d: RVP.make_agent(d)),
        ("marnie_munkidori", 0.111, up("mixed_ex3"), lambda d: RVP.make_agent(d)),
        ("lucario_ex", 0.095, up("lucario_ex"), lambda d: AC.make_agent(AC.LUCARIO_DECK)),
        ("dragapult", 0.057, up("dragapult"), lambda d: make_dragapult_agent()),
        ("crustle_LO", 0.033, up("crustle_control"), lambda d: make_lo_agent(d)),
    ]
    s = sum(r[1] for r in raw)
    return [(n, w / s, d, f) for n, w, d, f in raw]


def candidates():
    return [
        ("LO_mill", lambda: make_lo_agent(lo_deck())),
        ("v016_wall", lambda: load_built(os.path.join(WS, "exp007_anti_crustle", "build_v004"), "v004")),
        ("v019_sp3", lambda: load_built(os.path.join(WS, "exp047_pri_tobench", "build_sp3"), "sp3")),
        ("v020_arch", lambda: load_built(os.path.join(WS, "exp049_archaludon", "build_arch"), "arch")),
    ]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    pool = build_upper_pool()
    print(f"SILVER-BAND eval, n={n}/matchup, CRN={USE_CRN}")
    print("(for contrast, OUR-band weighted: LO-mill 0.692, v019 0.655, v016-wall 0.646, v020 0.604)\n")
    print("pool: " + ", ".join(f"{nm} {w*100:.1f}%" for nm, w, _, _ in pool) + "\n")

    rows = {}
    for cname, cfac in candidates():
        agent = cfac()
        print(f"=== {cname} ===", flush=True)
        tot = 0.0
        row = {}
        for oname, wgt, odeck, ofac in pool:
            t0 = time.time()
            kw = {"crn_seed_base": SEED_BASE + abs(hash(oname)) % 100000} if USE_CRN else {}
            st = run_gauntlet(agent, ofac(odeck), n_games=n, swap_sides=True, **kw)
            wr = st.winrate0
            row[oname] = wr
            tot += wgt * wr
            print(f"  {oname:17} w={wgt:.3f}  wr={wr:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        row["_upper_weighted"] = tot
        rows[cname] = row
        print(f"  --> SILVER-BAND WEIGHTED = {tot:.4f}\n", flush=True)

    json.dump(rows, open(os.path.join(HERE, f"upper_eval_n{n}.json"), "w"), indent=1)
    print("ranking (silver-band weighted):")
    for tag, r in sorted(rows.items(), key=lambda kv: -kv[1]["_upper_weighted"]):
        print(f"  {r['_upper_weighted']:.4f}  {tag}")
    print("\nElo: settled ~ mean_opp + 400*log10(p/(1-p)); silver band mean_opp ~= 930")
    for tag, r in sorted(rows.items(), key=lambda kv: -kv[1]["_upper_weighted"]):
        p = min(max(r["_upper_weighted"], 1e-6), 1 - 1e-6)
        print(f"  {tag:10} p={p:.3f} -> settles ~{930 + 400*math.log10(p/(1-p)):.0f}")


if __name__ == "__main__":
    main()
