"""exp070g — fix + measure: opponent_ex_pressure over-weights BENCHED ex.

Measured defect (error_rates.py, 303 real games): opponent_ex_pressure fired
1780 turns; 41.3% (735) were BENCH-ONLY -- a benched ex counted as pressure with
the SAME test as an active ex (attached+1 >= min). But a benched ex must be
PROMOTED first (retreat/switch, or wait for the active to be KO'd), so it is ~1
extra tempo away. The active branch's "attached+1>=min" means "one energy from
attacking"; applying the identical bar to a benched attacker means "one energy
AND one promotion" = ~2 tempo, yet it is treated as an immediate threat.

This is the ONLY code-reading candidate that survived the error-rate screen:
  - attack_energy_minimum typed-vs-count: 0.1% disagreement -> discarded
  - ready_crustle / active_is_ready_crustle: dead code (0 refs) -> discarded
  - lucario bench rules: reference cards absent from our deck -> dead -> discarded

It is also ORTHOGONAL to the oracle result: the oracle replaced ex IDENTITY
knowledge and made things worse (-0.0075) precisely because it asserted ex
pressure without regard to TIMING. This fix is about timing (bench vs active),
the one axis the oracle did not touch and we have not yet tried.

Arms (paired CRN, n each):
  base         -- shipped
  bench_strict -- benched ex counts only if ALREADY payable (attached >= min):
                  one promotion away, matching the active branch's one-tempo bar
  bench_off    -- benched ex never counts (only an active ex is pressure)

Gate: calibrated silver (V2) bar = 0.7661, no regression, 0 crash errors.
Escalate to n=600 only if a variant clears base by a margin that n=600 can resolve.
"""
from __future__ import annotations
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")
_n = [0]


def make_koff(arm: str):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffb{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    if arm != "base":
        act_ex = mod.active_pokemon
        is_ex = mod.is_ex_pokemon
        can_soon = mod.opponent_can_attack_soon
        att = mod.attached_energy_count
        amin = mod.attack_energy_minimum
        strict = (arm == "bench_strict")

        def patched(opponent):
            a = act_ex(opponent)
            if a is not None and is_ex(a) and can_soon(opponent):
                return True
            if strict:
                for p in opponent.bench:
                    # already payable -> only a promotion away (one tempo)
                    if is_ex(p) and att(p) >= amin(p):
                        return True
            return False

        mod.opponent_ex_pressure = patched
    return mod.agent


ARMS = ["base", "bench_strict"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash("benchex" + oname)) % 99991
        row = {}
        for arm in ARMS:
            st = run_gauntlet(make_koff(arm), fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=seed)
            row[arm] = st.winrate0
            row[arm + "_err"] = st.errors0 + st.errors1
        res[oname] = row
        print(f"  {oname:16s} w={w:.3f}  base {row['base']:.3f}  "
              f"strict {row['bench_strict']:.3f} ({row['bench_strict']-row['base']:+.3f})  "
              f"err={row['base_err']}/{row['bench_strict_err']}",
              flush=True)
    tot = sum(EB.SILVER_BAND.values())
    print()
    base_s = sum(w * res[o]["base"] for o, w in EB.SILVER_BAND.items()) / tot
    for arm in ARMS:
        s = sum(w * res[o][arm] for o, w in EB.SILVER_BAND.items()) / tot
        print(f"SILVER(V2) {arm:12s} {s:.4f}   delta vs base {s-base_s:+.4f}")
    print("bar (calibrated koff) = 0.7661")
    json.dump(res, open(os.path.join(HERE, "benchex.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
