"""exp070i — BUNDLE the two measured-correct threat-estimation fixes.

Both shipped predicates OVER-estimate incoming threat, in the same direction:

  1. opponent_ex_pressure: a benched ex is scored with the active's bar
     (attached+1 >= min), ignoring that it must be PROMOTED first.
     Measured: 41.3% of all fires were bench-only.  Fix = bench_strict.

  2. opponent_can_attack_soon: "attached + 1" hard-assumes the opponent attaches
     an energy next turn. Measured on 3393 real transitions: they attach ZERO
     87.3% of the time. Predicate says "can attack soon" 85.4% but only 70.7%
     were actually ready => 14.7% error. Dropping the +1 ("ready_now") gives
     5.4% error -- a 3x accuracy gain.
     (The acceleration hypothesis that motivated looking here was REFUTED:
      gain>=2 occurs 0.8% of turns and the predicate missed 0.0% of fast
      arrivals. The real defect is the opposite sign -- over-, not under-call.)

Because both errors inflate perceived threat, they should stack: the agent is
systematically too defensive (wall_mode on) when it should be milling.

Arms (paired CRN):
  base        -- shipped
  ready_now   -- fix 2 only
  bundle      -- fix 1 + fix 2

Gate: beat base by a margin n=600 can resolve, no regression, 0 crash errors.
Note opponent_can_attack_soon is also called INSIDE opponent_ex_pressure's active
branch, so fix 2 changes that path too; the bundle is not a clean sum of parts.
"""
from __future__ import annotations
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))

# CRITICAL (found 07-21): eval_both_bands picks the CRN harness only when "--crn"
# is in sys.argv. Without it, it caches the PLAIN cg engine, and every later
# `from harness_crn import run_gauntlet` is powerless -- the patched libcg.so that
# honours CG_CRN_SEED is never loaded, so "paired CRN" runs are silently unpaired.
# Symptom that exposed it: the same agent, same seed, twice -> different winrates.
if "--crn" not in sys.argv:
    sys.argv.append("--crn")

sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
assert EB.USE_CRN, "CRN harness not active"
import cg as _cg
assert "exp052_crn" in _cg.__file__, f"plain engine loaded: {_cg.__file__}"

sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")
_n = [0]


def make_koff(arm: str):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffn{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    act = mod.active_pokemon
    is_ex = mod.is_ex_pokemon
    att = mod.attached_energy_count
    amin = mod.attack_energy_minimum

    if arm in ("ready_now", "bundle"):
        def can_soon(opponent):
            a = act(opponent)
            return a is not None and att(a) >= amin(a)
        mod.opponent_can_attack_soon = can_soon
    else:
        can_soon = mod.opponent_can_attack_soon

    if arm in ("bundle", "bundle3"):
        def ex_pressure(opponent):
            a = act(opponent)
            if a is not None and is_ex(a) and can_soon(opponent):
                return True
            for p in opponent.bench:
                if is_ex(p) and att(p) >= amin(p):
                    return True
            return False
        mod.opponent_ex_pressure = ex_pressure

    if arm == "bundle3":
        # wall_mode's gate is `ex_pressure(...) OR shows_ex_evolution_line(...)`.
        # The second term is the ancestor check whose false-positive rate is 80.3%
        # (culprit: Dunsparce, 48 of 61 false-positive games). Fixing ex_pressure
        # alone cannot reduce wall_mode because the OR partner keeps firing.
        mod.EX_EVOLUTION_ANCESTORS = {n for n in mod.EX_EVOLUTION_ANCESTORS
                                      if n != "Dunsparce"}

    return mod.agent


ARMS = ["base", "bundle", "bundle3"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash("bundle" + oname)) % 99991
        row = {}
        for arm in ARMS:
            st = run_gauntlet(make_koff(arm), fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=seed)
            row[arm] = st.winrate0
            row[arm + "_err"] = st.errors0 + st.errors1
        res[oname] = row
        print(f"  {oname:16s} w={w:.3f}  base {row['base']:.3f}  "
              f"bundle {row['bundle']:.3f} ({row['bundle']-row['base']:+.3f})  "
              f"b3 {row['bundle3']:.3f} ({row['bundle3']-row['base']:+.3f})  "
              f"err={row['base_err']}/{row['bundle_err']}/{row['bundle3_err']}", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    print()
    b = sum(w * res[o]["base"] for o, w in EB.SILVER_BAND.items()) / tot
    for arm in ARMS:
        s = sum(w * res[o][arm] for o, w in EB.SILVER_BAND.items()) / tot
        print(f"SILVER(V2) {arm:10s} {s:.4f}   delta vs base {s-b:+.4f}")
    json.dump(res, open(os.path.join(HERE, f"bundle{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
