"""exp075 Stage 2 -- weakness map for the S1 survivor(s), n=200.

Adds the matchups S1 skipped: marnie (0.160 of the band), archaludon (0.073),
dragapult (0.027), lucario_ex (0.067), crustle_LO (0.012), plus the real
Dipplin deck (unmodelled 0-6 hole found in exp074) and the two S1 gates again
at higher n (mirror vs pub stock, head-to-head vs v030).

Candidate decks are passed as JSON paths; every candidate is piloted by
pub1034. No CRN pairing exists for pub1034 (its search uses Python random), so
these are LEVEL readings with SE ~0.035 at n=200 -- fine for a weakness map,
not for small A/B deltas.

Band aggregate: uses SILVER_BAND_V3 weights where a slot maps; mirror stands in
for the alakazam+alakazam_dun mass (0.413) since we would BE the Alakazam blob.

Usage: uv run python screen_s2.py deckA.json [deckB.json ...] [n]
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
SEED = 20260723
_n = [0]


def make_pub(deck=None):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"p75b_{_n[0]}", os.path.join(PUB, "main.py"))
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    n = 200
    if args and args[-1].isdigit():
        n = int(args.pop())
    assert args, "pass at least one deck json"
    opp = EB.opponents()
    E74 = os.path.join(WS, "exp074_nonex")

    gates = {
        "mirror":     (0.413, lambda: make_pub(None)),
        "marnie":     (0.160, lambda: opp["marnie"][1](opp["marnie"][0])),
        "pure_wall":  (0.093, lambda: AC.make_crustle_agent()),
        "archaludon": (0.073, lambda: opp["archaludon"][1](opp["archaludon"][0])),
        "lucario_ex": (0.067, lambda: opp["lucario_ex"][1](opp["lucario_ex"][0])),
        "dragapult":  (0.027, lambda: opp["dragapult"][1](opp["dragapult"][0])),
        "crustle_LO": (0.012, lambda: opp["crustle_LO"][1](opp["crustle_LO"][0])),
        "dipplin":    (0.0,   lambda: make_pub(json.load(open(os.path.join(E74, "real_dipplin_deck.json"))))),
        "koff_h2h":   (0.0,   lambda: load_built(V030, f"v030s2_{time.time_ns()}")),
    }
    out = {}
    print(f"exp075 S2 weakness map, n={n}. SE~{(0.25/n)**0.5:.3f}. pub1034 pilot.\n")
    print(f"{'deck':22}" + "".join(f"{g[:9]:>10}" for g in gates) + f"{'band~':>8}")
    for path in args:
        deck = json.load(open(path))
        name = os.path.basename(path).replace(".json", "")
        row, errs = {}, 0
        for gname, (w, gfac) in gates.items():
            st = run_gauntlet(make_pub(deck), gfac(), n_games=n, swap_sides=True,
                              crn_seed_base=SEED + abs(hash(name + gname)) % 99991)
            row[gname] = st.winrate0
            errs += st.errors0
            print(f"    {name} {gname}: {st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})", flush=True)
        wsum = sum(w for w, _ in gates.values())
        band = sum(w * row[g] for g, (w, _) in gates.items()) / wsum
        out[name] = {"wr": row, "band": band, "errs": errs}
        print(f"{name:22}" + "".join(f"{row[g]:10.3f}" for g in gates) + f"{band:8.3f}"
              + (f"   ERRORS={errs}" if errs else ""), flush=True)
    json.dump(out, open(os.path.join(HERE, f"s2_n{n}.json"), "w"), indent=1)
    print("\nref: koff v030 on this pool's V3 weights ~0.766 (lucario_v2 pool level, "
          "0.13 optimistic); real-ladder koff level 0.558.")


if __name__ == "__main__":
    main()
