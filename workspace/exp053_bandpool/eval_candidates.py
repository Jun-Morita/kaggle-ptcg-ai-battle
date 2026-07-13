"""exp053 step 2 -- "what deck should we actually bring to OUR band?"

Key structural fact driving this: the LB score is max(rating of the 2 eligible
submissions), and each rating reflects that agent's OWN whole-band winrate.
Matchup-level complementarity between the two eligible agents does NOT help
(you can't route a matchup to the other submission). So the only lever that
raises our LB is raising the BEST SINGLE agent's band-weighted winrate.
Current best = v016-wall at 0.659; Elo fixed-point says silver (~933 from our
~750) needs roughly 0.72-0.75.

So: instead of only patching our own agents, measure the CANDIDATE decks we can
actually pilot -- including the band's own strongest natives, whose dedicated
public pilots we already have -- against the same real-band pool used in
eval_band.py. This is "deck selection is the dominant lever" (established
repeatedly) applied for the FIRST TIME against a correctly-specified band pool.

Candidates added here beyond the 3 already measured:
  LO-mill    : the public Great Tusk library-out deck + its dedicated pilot
               (LB 1083.6). 20% of our band plays it and it beats v020 0.71.
  Alakazam   : the public 5th-place Alakazam agent + deck. 18% of our band
               plays it; v016-wall scores only 0.260 into it (our biggest
               single share-weighted bleed).

Self-matchups (candidate vs the same archetype in the pool) are real mirrors
and are kept -- a deck's mirror winrate is ~0.5 by construction and that IS
what it will face on the ladder against its own archetype.

Usage: uv run python eval_candidates.py [n_per_matchup]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp016_pubnb"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine, run_gauntlet  # noqa: E402
load_engine()

from eval_band import build_pool, load_built  # noqa: E402
from load_lo import make_lo_agent, lo_deck  # noqa: E402
from load_alakazam import make_alakazam_agent, alakazam_deck  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    pool = build_pool()

    # candidates: (name, agent_factory) -- decks are the pilots' own
    candidates = [
        ("cand_LO_mill", lambda: make_lo_agent()),
        ("cand_alakazam_pub", lambda: make_alakazam_agent()),
    ]

    print(f"candidate sweep vs REAL band pool, n={n}/matchup")
    print("(already measured in eval_band: v016-wall 0.659, v019 0.655, v020 0.604)\n")

    results = {}
    for cname, cfac in candidates:
        agent = cfac()
        print(f"=== {cname} ===", flush=True)
        tot = 0.0
        row = {}
        for name, wgt, deck, ofac in pool:
            t0 = time.time()
            st = run_gauntlet(agent, ofac(deck), n_games=n, swap_sides=True)
            wr = st.winrate0
            row[name] = wr
            tot += wgt * wr
            print(f"  {name:16} w={wgt:.2f}  wr={wr:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        row["_band_weighted"] = tot
        results[cname] = row
        print(f"  --> BAND-WEIGHTED WINRATE = {tot:.3f}\n", flush=True)

    json.dump(results, open(os.path.join(HERE, f"cand_eval_n{n}.json"), "w"), indent=1)
    print("candidate ranking (vs prior: v016-wall 0.659 / v019 0.655 / v020 0.604):")
    for tag, row in sorted(results.items(), key=lambda kv: -kv[1]["_band_weighted"]):
        print(f"  {row['_band_weighted']:.3f}  {tag}")


if __name__ == "__main__":
    main()
