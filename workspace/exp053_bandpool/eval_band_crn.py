"""exp053 step 3 -- decide v016-wall vs LO-mill with CRN-reduced variance.

The n=100 band eval left them statistically tied (v016-wall 0.659 vs LO-mill
0.646; the weighted-sum SE is ~0.02-0.03, so the 0.013 gap is noise). The
DECISION QUANTITY is band-weighted winrate (not a head-to-head, which barely
matters on the ladder -- they'd only meet in the 20% LO slice), so reduce the
variance ON THAT quantity: run both candidates against the SAME opponents with
the SAME dealt hands (exp052's CRN engine, measured 4.66x variance reduction),
and report the PAIRED per-matchup differences.

IMPORTANT (engine identity): this uses the CRN-patched LOCAL engine
(workspace/exp052_crn/cg -- official source, only ApiBattleStart's seed
handling changed). We put it on sys.path FIRST so every pilot in this process
imports that one `cg`, not data/sim_sample's. Never used to validate a real
submission build (build_submission.py keeps using the official engine).

Usage: uv run python eval_band_crn.py [n_per_matchup]
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

# CRN engine FIRST so all pilots share the patched cg
sys.path.insert(0, CRN)
from harness_crn import run_gauntlet, load_engine  # noqa: E402
load_engine()

for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp016_pubnb"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from eval_band import build_pool, load_built  # noqa: E402
from load_lo import make_lo_agent  # noqa: E402

SEED_BASE = 20260713


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    pool = build_pool()

    cands = [
        ("v016_wall", lambda: load_built(os.path.join(WS, "exp007_anti_crustle", "build_v004"), "v004")),
        ("LO_mill", lambda: make_lo_agent()),
    ]

    print(f"CRN paired band eval, n={n}/matchup, engine={CRN}")
    print("(non-CRN n=100 said: v016-wall 0.659 vs LO-mill 0.646 -- a statistical tie)\n")

    rows = {}
    for cname, cfac in cands:
        agent = cfac()
        print(f"=== {cname} ===", flush=True)
        tot = 0.0
        row = {}
        for name, wgt, deck, ofac in pool:
            t0 = time.time()
            # SAME seed sequence per opponent for BOTH candidates -> paired deals
            st = run_gauntlet(agent, ofac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=SEED_BASE + abs(hash(name)) % 100000)
            wr = st.winrate0
            row[name] = {"wr": wr, "w": st.wins0, "l": st.wins1, "d": st.draws}
            tot += wgt * wr
            print(f"  {name:16} w={wgt:.2f}  wr={wr:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        row["_band_weighted"] = tot
        rows[cname] = row
        print(f"  --> BAND-WEIGHTED = {tot:.4f}\n", flush=True)

    a, b = rows["v016_wall"], rows["LO_mill"]
    print(f"{'matchup':16} {'share':>5} {'v016':>7} {'LO':>7} {'delta(LO-v016)':>15}")
    var = 0.0
    for name, wgt, _, _ in pool:
        d = b[name]["wr"] - a[name]["wr"]
        # per-matchup SE of a difference of two paired proportions (conservative,
        # ignores the positive pairing correlation CRN induces -> overstates SE)
        se_m = math.sqrt(a[name]["wr"] * (1 - a[name]["wr"]) / n + b[name]["wr"] * (1 - b[name]["wr"]) / n)
        var += (wgt * se_m) ** 2
        print(f"{name:16} {wgt:5.2f} {a[name]['wr']:7.3f} {b[name]['wr']:7.3f} {d:+15.3f}")
    delta = b["_band_weighted"] - a["_band_weighted"]
    se = math.sqrt(var)
    print(f"\nband-weighted: v016_wall={a['_band_weighted']:.4f}  LO_mill={b['_band_weighted']:.4f}")
    print(f"delta(LO - v016) = {delta:+.4f}   SE(conservative) = {se:.4f}   z = {delta/se if se else 0:+.2f}")
    print("(CRN pairing makes the true SE SMALLER than this conservative estimate)")

    json.dump(rows, open(os.path.join(HERE, f"crn_band_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
