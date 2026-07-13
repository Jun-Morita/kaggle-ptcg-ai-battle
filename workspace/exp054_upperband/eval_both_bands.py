"""exp054 -- CORRECTED evaluation of every candidate on BOTH bands at once.

Two corrections vs everything before this:

1. **The crustle slot was represented by the wrong deck.** exp053 used the LO
   variant (most common single exact list) but the MAJORITY of that bucket is
   pure wall (82% of our band's crustle games, 65% of silver's) -- pure-wall
   builds just vary more so no single list wins the "most common list" vote.
   Here the bucket is split into pure_wall / crustle_LO at the measured ratio.
   This matters a lot: LO-mill scores 0.033 vs pure wall, while for v016-wall
   pure wall is its own MIRROR (~0.5) -- but the old pool credited v016-wall
   0.890 there (vs the LO variant). Both scores were distorted, in OPPOSITE
   directions, so the our-band ranking may flip.

2. Both bands are scored in one run so the ALTITUDE DERIVATIVE (does a
   candidate get better or worse as it climbs?) -- which exp054 showed is the
   thing that actually decides the Elo fixed point -- is read off directly.

Usage: uv run python eval_both_bands.py [n] [--crn]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
CRN = os.path.join(WS, "exp052_crn")

USE_CRN = "--crn" in sys.argv
if USE_CRN:
    sys.path.insert(0, CRN)
    from harness_crn import run_gauntlet, load_engine  # noqa: E402
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
from eval_band import load_built, band as our_band_deck  # noqa: E402

SEED = 20260715
BP = os.path.join(WS, "exp053_bandpool")


def up(name):
    return json.load(open(os.path.join(HERE, f"up_{name}.json")))


def pure_wall_deck():
    """The real pure-wall list if inspect_walls.py extracted one; else our own
    v016-wall list (AC.CRUSTLE_DECK), which IS a pure heal-wall."""
    p = os.path.join(HERE, "band_pure_wall.json")
    return json.load(open(p)) if os.path.exists(p) else list(AC.CRUSTLE_DECK)


# --- opponents (shared objects, different weights per band) ---
def opponents():
    return {
        "lucario_ex":   (list(AC.LUCARIO_DECK), lambda d: AC.make_agent(AC.LUCARIO_DECK)),
        "pure_wall":    (pure_wall_deck(),      lambda d: AC.make_crustle_agent()),
        "crustle_LO":   (lo_deck(),             lambda d: make_lo_agent(d)),
        "alakazam":     (our_band_deck("mixed_ex1"), lambda d: RVP.make_agent(d)),
        "alakazam_dun": (up("non_ex_attackers"), lambda d: RVP.make_agent(d)),
        "archaludon":   (up("mixed_ex4"),       lambda d: make_archaludon_agent()),
        "marnie":       (up("mixed_ex3"),       lambda d: RVP.make_agent(d)),
        "cinderace":    (our_band_deck("mixed_ex3"), lambda d: RVP.make_agent(d)),
        "dragapult":    (up("dragapult"),       lambda d: make_dragapult_agent()),
    }


# measured shares; crustle bucket split by the real pure-wall / LO ratio
OUR_BAND = {           # from v020's own ladder replays (700-770)
    "lucario_ex": 0.310,
    "pure_wall": 0.200 * 0.82,
    "crustle_LO": 0.200 * 0.18,
    "cinderace": 0.110,
    "alakazam": 0.180,
    "archaludon": 0.090,
    "dragapult": 0.070,
}
SILVER_BAND = {        # from tomatomato's replays (LB 948.8, the 933 cut)
    "alakazam_dun": 0.285,
    "archaludon": 0.264,
    "alakazam": 0.121,
    "marnie": 0.111,
    "lucario_ex": 0.095,
    "dragapult": 0.057,
    "pure_wall": 0.033 * 0.65,
    "crustle_LO": 0.033 * 0.35,
}


def candidates():
    return [
        ("v021_LOmill", lambda: make_lo_agent(lo_deck())),
        ("v019_sp3", lambda: load_built(os.path.join(WS, "exp047_pri_tobench", "build_sp3"), "sp3")),
        ("v016_wall", lambda: load_built(os.path.join(WS, "exp007_anti_crustle", "build_v004"), "v004")),
        ("v020_arch", lambda: load_built(os.path.join(WS, "exp049_archaludon", "build_arch"), "arch")),
    ]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    opp = opponents()
    needed = sorted(set(OUR_BAND) | set(SILVER_BAND))
    print(f"BOTH-BAND eval, n={n}/matchup, CRN={USE_CRN}")
    print("crustle bucket SPLIT: our band 82% pure-wall / 18% LO; silver 65/35\n")

    results = {}
    for cname, cfac in candidates():
        agent = cfac()
        print(f"=== {cname} ===", flush=True)
        wr = {}
        for oname in needed:
            deck, fac = opp[oname]
            t0 = time.time()
            kw = {"crn_seed_base": SEED + abs(hash(oname)) % 99991} if USE_CRN else {}
            st = run_gauntlet(agent, fac(deck), n_games=n, swap_sides=True, **kw)
            wr[oname] = st.winrate0
            print(f"  {oname:14} wr={st.winrate0:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        ours = sum(w * wr[o] for o, w in OUR_BAND.items())
        silv = sum(w * wr[o] for o, w in SILVER_BAND.items()) / sum(SILVER_BAND.values())
        results[cname] = {"wr": wr, "our_band": ours, "silver_band": silv,
                          "derivative": silv - ours}
        print(f"  --> OUR band {ours:.4f} | SILVER band {silv:.4f} | "
              f"altitude derivative {silv-ours:+.4f}\n", flush=True)

    json.dump(results, open(os.path.join(HERE, f"both_bands_n{n}.json"), "w"), indent=1)
    print(f"{'candidate':14} {'OUR band':>9} {'SILVER':>9} {'d(alt)':>8}")
    for c, r in sorted(results.items(), key=lambda kv: -kv[1]["silver_band"]):
        print(f"{c:14} {r['our_band']:9.4f} {r['silver_band']:9.4f} {r['derivative']:+8.4f}")
    print("\nA positive altitude derivative means the agent gets STRONGER as it climbs")
    print("(that, not the current-band score, is what sets the Elo fixed point).")


if __name__ == "__main__":
    main()
