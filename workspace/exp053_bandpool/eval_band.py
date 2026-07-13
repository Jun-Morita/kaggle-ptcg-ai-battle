"""exp053 -- re-rank our candidates against the REAL band pool.

Fixes the pool mis-specification found 2026-07-13: the band's biggest bleed
(crustle_control, 20% share, real wr 0.36) is actually the Great Tusk LO deck
+ its dedicated public pilot, NOT our pure-wall proxy (17/60 card overlap).
lucario_ex (31% share) our proxy already matches 60/60, so that one stays.

Opponents (weights = measured band shares from our own v020 ladder replays):
    lucario_ex        0.31   AC.LUCARIO_DECK + AC generic pilot (deck verified 60/60 real)
    crustle_LO        0.20   REAL Great Tusk LO deck + its REAL dedicated pilot  <- NEW
    mixed_ex3         0.11   band top list (Cinderace/Salvatore), generic pilot
    non_ex/mixed_ex1  0.18   Alakazam band list, generic pilot
    mixed_ex4         0.09   Archaludon (our own v020 archetype) -- dedicated pilot
    dragapult         0.07   public dragapult pilot

Candidates are BUILT ARTIFACTS (independent exec, no import contamination --
the exp017 lesson).

Usage: uv run python eval_band.py [n_per_matchup] [build_dir ...]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp007_anti_crustle"),
          os.path.join(WS, "exp020_deckinnov"), os.path.join(WS, "exp025_unkoable"),
          os.path.join(WS, "exp023_revenge"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine, run_gauntlet  # noqa: E402
load_engine()

import anti_crustle as AC  # noqa: E402
import revenge_policy as RVP  # noqa: E402
from load_dragapult import make_dragapult_agent  # noqa: E402
from load_archaludon import make_archaludon_agent  # noqa: E402
from load_lo import make_lo_agent, lo_deck  # noqa: E402


def load_built(build_dir, tag):
    spec = importlib.util.spec_from_file_location(f"b_{tag}", os.path.join(build_dir, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(build_dir)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def band(name):
    return json.load(open(os.path.join(HERE, f"band_{name}.json")))


# (name, weight, deck, agent_factory)
def build_pool():
    return [
        ("lucario_ex", 0.31, list(AC.LUCARIO_DECK), lambda d: AC.make_agent(AC.LUCARIO_DECK)),
        ("crustle_LO", 0.20, lo_deck(), lambda d: make_lo_agent()),
        ("mixed_ex3", 0.11, band("mixed_ex3"), lambda d: RVP.make_agent(d)),
        ("alakazam", 0.18, band("mixed_ex1"), lambda d: RVP.make_agent(d)),
        ("mixed_ex4_arch", 0.09, band("mixed_ex4"), lambda d: make_archaludon_agent()),
        ("dragapult", 0.07, band("dragapult"), lambda d: make_dragapult_agent()),
    ]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    builds = sys.argv[2:] or [
        os.path.join(WS, "exp049_archaludon", "build_arch"),        # v020
        os.path.join(WS, "exp047_pri_tobench", "build_sp3"),        # v019
        os.path.join(WS, "exp007_anti_crustle", "build_v004"),      # v016 wall
    ]
    pool = build_pool()
    print(f"band-weighted eval, n={n}/matchup\n")
    results = {}
    for bd in builds:
        tag = os.path.basename(bd)
        agent = load_built(bd, tag)
        print(f"=== {tag} ===")
        tot_w = 0.0
        row = {}
        for name, wgt, deck, fac in pool:
            t0 = time.time()
            st = run_gauntlet(agent, fac(deck), n_games=n, swap_sides=True)
            wr = st.winrate0
            row[name] = wr
            tot_w += wgt * wr
            print(f"  {name:16} w={wgt:.2f}  wr={wr:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        row["_band_weighted"] = tot_w
        results[tag] = row
        print(f"  --> BAND-WEIGHTED WINRATE = {tot_w:.3f}\n", flush=True)

    json.dump(results, open(os.path.join(HERE, f"band_eval_n{n}.json"), "w"), indent=1)
    print("ranking (band-weighted):")
    for tag, row in sorted(results.items(), key=lambda kv: -kv[1]["_band_weighted"]):
        print(f"  {row['_band_weighted']:.3f}  {tag}")


if __name__ == "__main__":
    main()
