"""exp076 / H18 -- open the SECOND CLOCK: +4 Basic {G} Energy for Superb Scissors.

Distinct from H17 (rejected): H17 added FIGHTING energy, which cannot pay Superb
Scissors' {G}{C}{C} cost, so it bought only dilution (-0.0755). H18 adds GRASS,
which turns Crustle -- the Pokemon that already sits active as our wall -- into
a 120-damage attacker whose text pierces opposing effects ("this attack's damage
isn't affected by any effects on your opponent's Active Pokemon"). Boss's Orders
x4 (nearly dead today) becomes a gust+KO prize plan against HP<=120 targets
(Abra/Kadabra/Dunsparce/Dudunsparce...).

Diagnostic already run (probe, 6 games/slot): with build_g2swap the pilot reaches 3
energy (never happened on v030), Superb Scissors is OFFERED and the pilot CHOSE
it 3/3 times unprompted -- the clock works without any policy change.

build_g2swap: -1 Jumbo Ice Cream (dead: needs 3+ energy), -2 Lisia's Appeal,
-1 Ultra Ball, +4 Basic {G} Energy. Energy 8 -> 12.

Measured on the lucario_v2 pool, where CRN is verified to hold (crn_control.py).
Its LEVEL is optimistic by ~0.13 (H7), but this is a paired A/B, which is what
that pool is still good for. Same cuts as e12, so e12 (n=200, -0.0755) acts as
the dilution-only control arm: g4 - e12 isolates the value of the grass clock.

Caveat: the pool's Alakazam slots are decided by the opponent decking ITSELF out
(exp074 Stage 8), so gains there may be for the wrong reason. The matchups where
we actually attack -- pure_wall, marnie, archaludon, crustle_LO -- carry the
believable signal.

Usage: uv run python eval_g4.py [n]
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
        "g2": os.path.join(HERE, "build_g2swap")}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    opp = EB.opponents()
    res = {a: {} for a in ARMS}
    print(f"H18 grass clock (swap 2 Mist -> 2 Basic Grass (zero dilution) for Superb Scissors), n={n}/matchup, CRN, lucario_v2 pool\n")
    print(f"{'matchup':14}{'weight':>8}{'base':>9}{'g2':>9}{'delta':>9}   errors")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash(oname)) % 99991
        errs = []
        for arm, path in ARMS.items():
            st = run_gauntlet(load_built(path, f"{arm}_{oname}"), fac(deck),
                              n_games=n, swap_sides=True, crn_seed_base=seed)
            res[arm][oname] = st.winrate0
            errs.append((st.errors0, st.errors1))
        d = res["g2"][oname] - res["base"][oname]
        print(f"{oname:14}{EB.SILVER_BAND[oname]:8.4f}{res['base'][oname]:9.3f}"
              f"{res['g2'][oname]:9.3f}{d:+9.3f}   {errs}", flush=True)

    tot = sum(EB.SILVER_BAND.values())
    band = {a: sum(w * res[a][o] for o, w in EB.SILVER_BAND.items()) / tot
            for a in ARMS}
    print(f"\nband base {band['base']:.4f}   g4 {band['g2']:.4f}   "
          f"delta {band['g2']-band['base']:+.4f}")
    print("Reminder: this pool's LEVEL is ~0.13 optimistic (H7); only the delta "
          "is meaningful, and only if errors are 0.")
    json.dump({"per_matchup": res, "band": band},
              open(os.path.join(HERE, f"g2_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
