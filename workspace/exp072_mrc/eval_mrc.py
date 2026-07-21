"""exp072 — public "Metagame-Resilient Control" (prvsiyan) vs our shipped koff.

Why this one matters more than the usual sweep candidate: its deck is 60/60
IDENTICAL to our koff deck. So this is a clean deck-controlled comparison of
PILOTS -- exactly the axis exp055 showed is worth up to 0.5 winrate on a fixed
60 cards. Adopting it would carry zero deck risk.

Provenance (from the notebook): an adaptation of soutasakurai's public
LibraryOut/Crustle/Great Tusk policy, which advertises a historical max Elo of
1208; the author's stated change is a Xerosic priority once a Lucario-line
pokemon is actually visible.

Sweep filter 1 (author's own ladder standing) is a CAUTION, not a pass:
prvsiyan sits at rank 825 / 823.2, and the notebook's attached score is 899.2 --
both below our koff fixed point (~915-922) and below the silver cut (916.8).
The exp066 lesson was that an unbacked title claim predicts a weak agent. We
measure anyway because the deck-identity makes the pilot comparison unusually
informative even if we do not adopt.

Two measurements:
  A. band gate  -- their pilot over our calibrated silver pool, vs bar 0.7661
  B. mirror h2h -- their pilot vs our koff, same 60 cards, both seats

Harness note (bug found 07-21): eval_both_bands only selects the CRN harness
when "--crn" is in sys.argv; without it the PLAIN engine is cached and every
"paired CRN" run is silently unpaired. Asserted below.
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

AGENT_DIR = os.path.join(HERE, "agent")
KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")
_n = [0]


def _load(path_dir, tag):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"{tag}{_n[0]}", os.path.join(path_dir, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(path_dir)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def make_mrc():
    m = _load(AGENT_DIR, "mrc")
    # Their read_deck_csv() runs at CALL time (ours runs at import), so it looks
    # for deck.csv in the *current* cwd and falls back to the Kaggle sandbox path.
    # Bind it to the notebook's exact 60 cards instead of depending on cwd.
    deck = [int(x) for x in open(os.path.join(AGENT_DIR, "deck.csv")).read().split()]
    assert len(deck) == 60
    m.read_deck_csv = lambda: list(deck)
    fn = m.agent
    # their signature is agent(obs_dict, configuration=None); harness passes one arg
    return lambda obs: fn(obs)


def make_koff():
    return _load(KOFF_DIR, "koff").agent


def main():
    n = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(
        a.isdigit() for a in sys.argv[1:]) else 200
    opp = EB.opponents()

    print(f"=== A. band gate (n={n}/matchup, true CRN) -- bar = koff 0.7661 ===")
    wr, errs = {}, 0
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        t0 = time.time()
        st = run_gauntlet(make_mrc(), fac(deck), n_games=n, swap_sides=True,
                          crn_seed_base=EB.SEED + abs(hash("mrc" + oname)) % 99991)
        wr[oname] = st.winrate0
        errs += st.errors0 + st.errors1
        print(f"  {oname:16s} w={w:.3f} wr={st.winrate0:.3f} "
              f"err=({st.errors0},{st.errors1}) {time.time()-t0:.0f}s", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    band = sum(w * wr[o] for o, w in EB.SILVER_BAND.items()) / tot
    print(f"  SILVER(V2) weighted: {band:.4f}   (koff bar 0.7661)   total errors {errs}")

    print(f"\n=== B. mirror head-to-head vs our koff, identical 60 cards (n={n}) ===")
    st = run_gauntlet(make_mrc(), make_koff(), n_games=n, swap_sides=True,
                      crn_seed_base=EB.SEED + 4242)
    print(f"  their pilot vs koff: {st.winrate0:.3f} "
          f"({st.wins0}-{st.wins1}-{st.draws})  err=({st.errors0},{st.errors1})")
    print("  >0.5 means their pilot is stronger on the SAME deck")

    json.dump({"band": wr, "band_weighted": band,
               "mirror_vs_koff": st.winrate0, "errors": errs},
              open(os.path.join(HERE, f"mrc{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
