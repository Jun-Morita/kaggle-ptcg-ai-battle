"""exp070d — counterfactual: the ex-LINE (ancestor) false positive.

Ground-truth finding (truth_check.py, 303 real ladder games):
  opponent HAD ex  -> predicate fires 97.4%, misses 2.6%   (detection is fine)
  opponent had NO ex -> predicate fires 80.3%              (FALSE POSITIVE)
  our winrate vs no-ex opponents: 0.303   vs ex opponents: 0.643

Mechanism: EX_EVOLUTION_ANCESTORS is every name that is transitively an ancestor
of ANY ex card in the whole pool (105 names). Many basics evolve into BOTH an ex
and a non-ex line, so the mere sight of such a basic asserts "ex pressure".
Culprit breakdown over the 61 false-positive games: Dunsparce 48, Applin 6,
Dipplin 6, Duraludon 5, Riolu 2. Dunsparce dominates -- and it is the core of the
non-ex attacker archetype, which is our LARGEST matchup (weight 0.289) and our
LARGEST loss source (28.7% of losses).

Pool validity checked before running (the exp070 lesson): in the pool's
alakazam_dun matchup, Dunsparce appears on their board 26/42 of our decisions and
the predicate fires exactly 26 times -- 1:1, so the pool exercises this path
faithfully. (Contrast pure_wall, where the pool opponent never plays its ex.)

Arms:
  base      -- shipped koff
  no_anc    -- ancestor path made inert (require a REAL ex on board)
  no_dun    -- drop only Dunsparce, keep early detection for genuine ex lines

Paired CRN. Gate: calibrated silver (V2) bar = 0.7661, plus no regression.
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


def make_koff(arm: str):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffx{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if arm == "no_anc":
        mod.EX_EVOLUTION_ANCESTORS = set()
    elif arm == "no_dun":
        mod.EX_EVOLUTION_ANCESTORS = {n for n in mod.EX_EVOLUTION_ANCESTORS
                                      if n != "Dunsparce"}
    return mod.agent


ARMS = ["base", "no_anc", "no_dun"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash("exline" + oname)) % 99991
        row = {}
        for arm in ARMS:
            st = run_gauntlet(make_koff(arm), fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=seed)      # identical seeds across arms
            row[arm] = st.winrate0
            row[arm + "_err"] = st.errors0 + st.errors1
        res[oname] = row
        print(f"  {oname:16s} w={w:.3f}  base {row['base']:.3f}  "
              f"no_anc {row['no_anc']:.3f} ({row['no_anc']-row['base']:+.3f})  "
              f"no_dun {row['no_dun']:.3f} ({row['no_dun']-row['base']:+.3f})  "
              f"err={row['base_err']}/{row['no_anc_err']}/{row['no_dun_err']}", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    print()
    scores = {}
    for arm in ARMS:
        s = sum(w * res[o][arm] for o, w in EB.SILVER_BAND.items()) / tot
        scores[arm] = s
        print(f"SILVER(V2) {arm:8s} {s:.4f}   delta vs base {s-scores['base']:+.4f}")
    print(f"\nbar (calibrated koff) = 0.7661")
    json.dump({"per_matchup": res, "silver": scores},
              open(os.path.join(HERE, "exline.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
