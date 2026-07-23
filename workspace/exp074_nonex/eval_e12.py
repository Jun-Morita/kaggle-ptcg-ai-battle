"""exp074 / H17 -- is our deck energy-starved? (8 -> 12 energy)

Why this is the live hypothesis after H2 died and H1 turned out to be draw-limited:

  - We attack on only 55.2% of our turns overall, and on 7-15% of turns against
    the Alakazam（フーディン）family, which is 41% of the band weight and our worst
    real matchup. There we mill 1.4-2.4 cards a game and take 0 prizes -- i.e. we
    have no win condition at all.
  - Our active holds 0 energy on most turns and never reached 3 in any sample.
  - Land Collapse (our only clock) costs {C}{C}: any two energy will do. So the
    mill is gated purely on GETTING two energy down, and we run 8 energy in 60.

Also fixed here, found while reading the list:
  - Superb Scissors, Crustle's 120, costs {G}{C}{C} -- a GRASS energy. We run
    none, so that attack is permanently unusable. (This, not scarcity, is why the
    H2 oracle never fired.)
  - Jumbo Ice Cream heals "a Pokemon with 3 or more Energy attached". We never
    reach 3. Dead card.
  - Fighting Gong searches "a Basic {F} Energy card or a Basic {F} Pokemon". We
    ran no Basic {F} Energy, so its energy mode was dead -- adding Basic {F}
    Energy turns 4 existing slots into real energy tutors at no cost.

build_e12: -1 Jumbo Ice Cream, -2 Lisia's Appeal, -1 Ultra Ball, +4 Basic {F}
Energy. Energy 8 -> 12, and Fighting Gong x4 becomes live.

Measured on the lucario_v2 pool, where CRN is verified to hold (crn_control.py).
Its LEVEL is optimistic by ~0.13 (H7), but this is a paired A/B, which is what
that pool is still good for.

Caveat stated up front: the pool's Alakazam slots are decided by the opponent
decking ITSELF out (Stage 8), so a mill improvement may show up there for the
wrong reason. Watch the matchups where we actually attack -- pure_wall,
archaludon, marnie, crustle_LO, dragapult -- and the mill/attack counters.

Usage: uv run python eval_e12.py [n]
"""
from __future__ import annotations
import os, sys, json, time

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
from eval_band import load_built

ARMS = {"base": os.path.join(WS, "exp071_bundlefix", "build"),
        "e12": os.path.join(HERE, "build_e12")}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    opp = EB.opponents()
    res = {a: {} for a in ARMS}
    print(f"H17 energy 8->12, n={n}/matchup, CRN, lucario_v2 pool\n")
    print(f"{'matchup':14}{'weight':>8}{'base':>9}{'e12':>9}{'delta':>9}   errors")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash(oname)) % 99991
        errs = []
        for arm, path in ARMS.items():
            st = run_gauntlet(load_built(path, f"{arm}_{oname}"), fac(deck),
                              n_games=n, swap_sides=True, crn_seed_base=seed)
            res[arm][oname] = st.winrate0
            errs.append((st.errors0, st.errors1))
        d = res["e12"][oname] - res["base"][oname]
        print(f"{oname:14}{EB.SILVER_BAND[oname]:8.4f}{res['base'][oname]:9.3f}"
              f"{res['e12'][oname]:9.3f}{d:+9.3f}   {errs}", flush=True)

    tot = sum(EB.SILVER_BAND.values())
    band = {a: sum(w * res[a][o] for o, w in EB.SILVER_BAND.items()) / tot
            for a in ARMS}
    print(f"\nband base {band['base']:.4f}   e12 {band['e12']:.4f}   "
          f"delta {band['e12']-band['base']:+.4f}")
    print("Reminder: this pool's LEVEL is ~0.13 optimistic (H7); only the delta "
          "is meaningful, and only if errors are 0.")
    json.dump({"per_matchup": res, "band": band},
              open(os.path.join(HERE, f"e12_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
