"""exp074 stage 3 -- the UNMODELLED deck: Dipplin.

Stage 2 split the non_ex_attackers bucket by family and found it is not one deck:

    Alakazam family   7-20   wr 0.350   (13 losses)
    Dipplin           0-6    wr 0.000   ( 6 losses)   <-- NOT IN OUR POOL AT ALL
    other (Phantump)  0-1    wr 0.000

Our pool models only the Alakazam half, so the whole Dipplin archetype -- 30% of
all our non-ex losses and a clean 0-6 -- has never once been evaluated locally.
An unmodelled 0.000 matchup is a bigger instrument hole than a mispredicted one.

This measures v030 against the real Dipplin list under every pilot we own. Read it
the same way as stage 1: if all pilots report ~0.8 while reality is 0.000, the deck
is not the story and we have a pilot-fidelity problem across the board; if some
pilot lands near 0.0-0.3, we have a usable new pool slot.

Usage: uv run python eval_dipplin.py [n]
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

sys.path.insert(0, os.path.join(WS, "exp007_anti_crustle"))
sys.path.insert(0, os.path.join(WS, "exp023_revenge"))
import anti_crustle as AC
import revenge_policy as RVP
from eval_band import load_built

SEED = 20260722
PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def make_pub1034(deck):
    """pub1034's search-augmented pilot, driving an arbitrary deck.

    Its main.py calls read_deck_csv() at agent-construction time and resolves the
    path relative to cwd (the exp066/exp072 failure mode), so inject the deck
    before exec instead of relying on the file."""
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
    deck = json.load(open(os.path.join(HERE, "real_dipplin_deck.json")))
    ours = load_built(os.path.join(WS, "exp071_bundlefix", "build"), "v030")

    cands = [
        ("RVP (pool default pilot)", lambda: RVP.make_agent(deck)),
        ("AC generic",               lambda: AC.make_agent(deck)),
        ("pub1034 search-augmented", lambda: make_pub1034(deck)),
    ]
    print(f"v030 vs REAL Dipplin deck, n={n}, CRN   (real ladder = 0.000, 0-6)")
    out = {}
    for name, fac in cands:
        t0 = time.time()
        st = run_gauntlet(ours, fac(), n_games=n, swap_sides=True,
                          crn_seed_base=SEED)
        out[name] = st.winrate0
        print(f"  {name:26s} our wr {st.winrate0:.3f}  "
              f"({st.wins0}-{st.wins1}-{st.draws})  err=({st.errors0},{st.errors1})  "
              f"{time.time()-t0:.0f}s", flush=True)
    json.dump(out, open(os.path.join(HERE, f"dipplin_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
