"""exp070 step 3: counterfactual — force should_wall_mode OFF on the SHIPPED build.

Why re-test something already dismissed:
  - wall_OFF was measured ONCE (07-14): n=100, archaludon ONLY, and BEFORE KO_OFF
    shipped. Point estimate was baseline 0.680 -> wall OFF 0.720 (+0.040), correctly
    dismissed as noise at that n (SE~0.047).
  - It has NEVER been measured on the current post-KO_OFF build, where wall_mode
    operates in a different context (the race branch it used to interact with is gone).
  - Today's predicate scan shows wall_mode firing MORE in losses in 6/6 matchups
    where it is live (combined weight 0.740 of the calibrated band).

The W/L split alone is NOT evidence -- reverse causation is very plausible (losing
=> more opposing ex pressure visible => wall_mode fires). This counterfactual is
what discriminates, exactly as probe_arch/probe_wall_force did for ko_mode.

Paired CRN: both arms see identical seeds per matchup, so the delta is the gate alone.
Bar: calibrated koff = 0.7661 (exp069 V2 pool).
"""
from __future__ import annotations
import os, sys, time, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")
_n = [0]


def make_koff(wall_off: bool):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffw{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if wall_off:
        mod.should_wall_mode = lambda me, opponent, state: False
    return mod.agent


def verify():
    """Confirm the override actually changes behaviour (exp066 rule)."""
    base, off = make_koff(False), make_koff(True)
    opp = EB.opponents()
    deck, fac = opp["alakazam_dun"]
    a = run_gauntlet(base, fac(deck), n_games=10, swap_sides=True, crn_seed_base=31337)
    b = run_gauntlet(off, fac(deck), n_games=10, swap_sides=True, crn_seed_base=31337)
    print(f"[verify] same seeds, baseline {a.winrate0:.3f} vs wall_OFF {b.winrate0:.3f} "
          f"-- {'behaviour DIFFERS (good)' if a.winrate0 != b.winrate0 else 'IDENTICAL: override may be inert'}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    verify()
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        base = EB.SEED + abs(hash("walloff" + oname)) % 99991
        row = {}
        for label, flag in (("base", False), ("wall_off", True)):
            t0 = time.time()
            st = run_gauntlet(make_koff(flag), fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=base)
            row[label] = st.winrate0
            row[label + "_err"] = (st.errors0, st.errors1)
        res[oname] = row
        print(f"  {oname:16s} w={w:.3f}  base {row['base']:.3f}  wall_OFF {row['wall_off']:.3f}  "
              f"delta {row['wall_off']-row['base']:+.3f}  err={row['base_err']}/{row['wall_off_err']}",
              flush=True)
    tot = sum(EB.SILVER_BAND.values())
    b = sum(w * res[o]["base"] for o, w in EB.SILVER_BAND.items()) / tot
    f = sum(w * res[o]["wall_off"] for o, w in EB.SILVER_BAND.items()) / tot
    print(f"\nSILVER(V2 calibrated): base {b:.4f}  wall_OFF {f:.4f}  DELTA {f-b:+.4f}")
    json.dump(res, open(os.path.join(HERE, "walloff.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
