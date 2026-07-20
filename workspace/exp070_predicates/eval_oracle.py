"""exp070e — ORACLE bound: what is PERFECT opponent-deck knowledge worth?

The question behind this (user's): maybe the deck-identification mechanism is
simply too naive -- a single-card board check ("is an ex ancestor visible")
standing in for real archetype inference. Before building a proper classifier,
measure its CEILING.

We replace `opponent_has_ex_or_ex_line_pressure` with the TRUE answer, taken from
the opponent's actual decklist (known for every pool matchup). No classifier can
beat this: it is perfect, instant, zero-false-positive, zero-false-negative
knowledge of whether the opponent runs ex.

  ex=False : alakazam_dun (w 0.289), crustle_LO (w 0.033)   -- 0.322 of the band
  ex=True  : everything else

Reading:
  oracle ~= base  -> the information channel is NOT the bottleneck. koff has only
      one opponent-conditional switch left (wall_mode; ko_mode is disabled by
      KO_OFF), so better knowledge has almost nothing to act on. Building a
      richer classifier would be pointless -- the ACTION repertoire is the limit,
      not the perception.
  oracle >> base  -> perception is the bottleneck and a real classifier is worth
      building; the gap sizes the budget.

This is the mandatory step (2) dynamic-range measurement from the exp060 rule,
applied to "opponent deck identification" as the lever.
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

# ground truth from the actual pool decklists (verified: is_ex_card over the list)
TRUE_EX = {
    "alakazam_dun": False, "crustle_LO": False,
    "alakazam": True, "marnie": True, "archaludon": True,
    "lucario_ex": True, "pure_wall": True, "dragapult": True,
}


def make_koff(arm, oname):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffo{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if arm == "oracle":
        truth = TRUE_EX[oname]
        mod.opponent_has_ex_or_ex_line_pressure = lambda opponent, _t=truth: _t
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash("oracle" + oname)) % 99991
        row = {}
        for arm in ("base", "oracle"):
            st = run_gauntlet(make_koff(arm, oname), fac(deck), n_games=n,
                              swap_sides=True, crn_seed_base=seed)
            row[arm] = st.winrate0
        res[oname] = row
        print(f"  {oname:16s} w={w:.3f} trueEx={str(TRUE_EX[oname]):5s}  "
              f"base {row['base']:.3f}  oracle {row['oracle']:.3f}  "
              f"delta {row['oracle']-row['base']:+.3f}", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    b = sum(w * res[o]["base"] for o, w in EB.SILVER_BAND.items()) / tot
    o_ = sum(w * res[o]["oracle"] for o, w in EB.SILVER_BAND.items()) / tot
    print(f"\nSILVER(V2)  base {b:.4f}   ORACLE {o_:.4f}   CEILING {o_-b:+.4f}")
    print("(this is the upper bound for ANY opponent-deck classifier "
          "acting through this predicate)")
    json.dump(res, open(os.path.join(HERE, "oracle.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
