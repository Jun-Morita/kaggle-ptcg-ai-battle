"""exp075 Stage 1 -- coarse screen of candidate decks (goal: silver).

Candidates (see SESSION_NOTES.md): all piloted by pub1034's search-augmented
policy (the only strong non-lucario pilot we own), vs three gates:

    mirror  : vs pub1034 STOCK      (proxy for the 41% Alakazam blob; R2)
    koff    : vs our v030 build     (do we beat our own current deck?)
    wall    : vs AC pure wall       (R4; v025 evidence says Alakazam >> walls)

pub1034's search samples from Python's random -> CRN does NOT pair these
(exp074 control). n=100/side => SE ~0.05 unpaired. Read only large gaps.

Usage: uv run python screen_s1.py [n]
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
import anti_crustle as AC
from eval_band import load_built

PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
V030 = os.path.join(WS, "exp071_bundlefix", "build")
SEED = 20260722
_n = [0]


def make_pub(deck=None):
    """pub1034 pilot; optionally driving a different 60-card list."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"p75_{_n[0]}", os.path.join(PUB, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(PUB)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if deck is not None:
        mod.read_deck_csv = lambda: list(deck)
    return mod.agent


def dj(path):
    return json.load(open(path))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
    E74 = os.path.join(WS, "exp074_nonex")
    cands = {
        "A_pub_stock":   lambda: make_pub(None),
        "B_hammer":      lambda: make_pub(dj(os.path.join(E74, "real_nonex_worst.json"))),
        "C_nonex_freq":  lambda: make_pub(dj(os.path.join(E74, "real_nonex_deck.json"))),
        "D_dipplin":     lambda: make_pub(dj(os.path.join(E74, "real_dipplin_deck.json"))),
    }
    gates = {
        "mirror": lambda: make_pub(None),
        "koff":   lambda: load_built(V030, f"v030_{time.time_ns()}"),
        "wall":   lambda: AC.make_crustle_agent(),
    }
    out = {}
    print(f"exp075 S1 screen, n={n}/gate. SE~{(0.25/n)**0.5:.3f} unpaired; read big gaps only.\n")
    print(f"{'candidate':14}" + "".join(f"{g:>9}" for g in gates) + "   err")
    for cname, cfac in cands.items():
        row, errs = {}, 0
        for gname, gfac in gates.items():
            st = run_gauntlet(cfac(), gfac(), n_games=n, swap_sides=True,
                              crn_seed_base=SEED + abs(hash(cname + gname)) % 99991)
            row[gname] = st.winrate0
            errs += st.errors0
        out[cname] = row
        print(f"{cname:14}" + "".join(f"{row[g]:9.3f}" for g in gates) + f"   {errs}", flush=True)
    json.dump(out, open(os.path.join(HERE, f"s1_n{n}.json"), "w"), indent=1)
    print("\ngate refs: koff-vs-pub_stock from exp074 was ~0.60 our side "
          "(i.e. a candidate needs koff>0.5 here to beat our current deck).")


if __name__ == "__main__":
    main()
