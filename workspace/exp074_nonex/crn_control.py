"""exp074 / control -- is CRN still pairing when the OPPONENT is pub1034?

The koff run (eval_onepilot_koff.py) produced differences where none are possible.
koff and v030 differ by exactly one line, which only edits the ex-evolution
ancestor set for Dunsparce（ノコッチ）. Under the lucario_v2 pool that showed up
exactly where it should: alakazam_dun 0.810->0.847, alakazam 0.890->0.893, and
every other matchup byte-identical (fix_only_wins = base_only_wins = 0).

Under pub1034 the same two builds diverge on marnie (0.635 vs 0.705) and on
pure_wall (0.690 vs 0.630) -- decks the fix cannot touch. Either the fix somehow
fires there, or CRN is no longer holding the games identical.

The likely cause: pub1034 is search-augmented and samples its own determinizations
from Python's `random`, which CG_CRN_SEED does not control. If so, every paired
comparison run against a pub1034 opponent has lost its variance reduction, and
differences of ~0.07 at n=200 are just noise (SE of a paired-turned-unpaired diff
is about 0.05).

This is the same control that caught the CRN bug: run the SAME agent twice with
the SAME seed. Identical => CRN holds. Different => it does not.

Usage: uv run python crn_control.py [n]
"""
from __future__ import annotations
import os, sys, json, importlib.util

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
sys.path.insert(0, os.path.join(WS, "exp023_revenge"))
import revenge_policy as RVP
from eval_band import load_built

SEED = 20260715
PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def make_pub1034(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pubc_{_n[0]}", os.path.join(PUB, "main.py"))
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
    deck, _ = EB.opponents()["marnie"]
    seed = SEED + abs(hash("marnie")) % 99991

    print(f"same agent, same seed, twice. n={n}. Identical => CRN holds.\n")
    for label, fac in (("pub1034 (search-augmented)", lambda: make_pub1034(deck)),
                       ("RVP (lucario_v2, control)", lambda: RVP.make_agent(deck))):
        runs = []
        for i in (1, 2):
            ours = load_built(os.path.join(WS, "exp071_bundlefix", "build"), f"v030_{label}_{i}")
            st = run_gauntlet(ours, fac(), n_games=n, swap_sides=True, crn_seed_base=seed)
            runs.append((st.winrate0, st.wins0, st.wins1, st.draws))
        a, b = runs
        ok = "IDENTICAL -> CRN holds" if a == b else "DIFFERENT -> CRN broken here"
        print(f"{label}")
        print(f"   run1 wr={a[0]:.3f} ({a[1]}-{a[2]}-{a[3]})")
        print(f"   run2 wr={b[0]:.3f} ({b[1]}-{b[2]}-{b[3]})   {ok}\n")


if __name__ == "__main__":
    main()
