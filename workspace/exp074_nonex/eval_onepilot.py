"""exp074 stage 4 -- is our whole pool ONE opponent brain? (hypothesis H7)

Stage 3 measured v030 vs the real Dipplin deck and RVP and AC returned BYTE-
IDENTICAL records (148-52-0 both times), the same signature that exposed the CRN
bug. Cause found: both load the same base policy `policies/lucario_v2.py`; RVP
adds a PATCH_SRC that is DECK-DISPATCHED (Trevenant/Hop's non-ex) and therefore
inert on Alakazam and Dipplin. So on those decks RVP is exactly AC.

Auditing opponents() by pilot rather than by deck:

    lucario_ex, pure_wall, alakazam, alakazam_dun, marnie, cinderace  -> lucario_v2
    crustle_LO, archaludon, dragapult                                 -> other

Weighted by SILVER_BAND_V3 that is **86.8% of the band driven by one pilot**. Every
gate, every CMA-ES tuning run (exp058/exp060), every adoption verdict this year was
scored mostly against a single opponent brain we have been implicitly fitting to
for months. That is textbook single-opponent overfitting, and it predicts exactly
the optimism we see:

    pool band-weighted     0.766
    real ladder (147 gms)  0.558      gap 0.208
    per-matchup pilot gap  0.210      (stage 1: 0.820 -> 0.610 on the real deck)

The two gaps agreeing to 0.002 is the reason to take this seriously: it says the
pool->reality error is NOT the archetype weights (calibrated twice already, V2/V3)
but the pilot monoculture.

This script re-scores v030 with the ONE genuinely different and stronger brain we
own (pub1034's search-augmented pilot) driving every deck, and reports the band
number. Pre-registered read:

  - lands near 0.558  -> H7 confirmed, the pool must be re-piloted before H1-H4
  - stays near 0.766  -> H7 rejected, the gap is elsewhere (pilot is not the cause)

Nothing in eval_both_bands.py is modified; this only measures.

Usage: uv run python eval_onepilot.py [n]
"""
from __future__ import annotations
import os, sys, json, time, importlib.util

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

SEED = 20260715          # same base as eval_both_bands, so slots stay comparable
PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def make_pub1034(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pub74_{_n[0]}", os.path.join(PUB, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(PUB)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.read_deck_csv = lambda: list(deck)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    ours = load_built(os.path.join(WS, "exp071_bundlefix", "build"), "v030")
    opp = EB.opponents()
    W = EB.SILVER_BAND

    # the five slots currently piloted by lucario_v2 that carry band weight
    REPILOT = ["alakazam_dun", "marnie", "alakazam", "pure_wall", "lucario_ex"]

    baseline = json.load(open(os.path.join(WS, "exp070_predicates", "nodun600.json")))
    base = {k: v["no_dun"] for k, v in baseline.items()}

    print(f"v030, same decks, pub1034 pilot instead of lucario_v2. n={n}, CRN")
    print(f"{'slot':14}{'weight':>8}{'lucario_v2':>12}{'pub1034':>10}{'delta':>9}")
    wr = dict(base)
    for name in REPILOT:
        deck, _ = opp[name]
        t0 = time.time()
        st = run_gauntlet(ours, make_pub1034(deck), n_games=n, swap_sides=True,
                          crn_seed_base=SEED + abs(hash(name)) % 99991)
        wr[name] = st.winrate0
        print(f"{name:14}{W[name]:8.4f}{base[name]:12.3f}{st.winrate0:10.3f}"
              f"{st.winrate0-base[name]:+9.3f}   err=({st.errors0},{st.errors1}) "
              f"{time.time()-t0:.0f}s", flush=True)

    tot = sum(W.values())
    old = sum(W[k] * base[k] for k in W) / tot
    new = sum(W[k] * wr[k] for k in W) / tot
    print(f"\nband (lucario_v2 pool) {old:.4f}")
    print(f"band (re-piloted)      {new:.4f}")
    print(f"real ladder, 147 games 0.5578")
    print(f"\nresidual vs reality: {old-0.5578:+.4f} -> {new-0.5578:+.4f}")
    json.dump({"wr": wr, "band_old": old, "band_new": new},
              open(os.path.join(HERE, f"onepilot_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
