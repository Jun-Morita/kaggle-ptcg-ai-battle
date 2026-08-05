"""Put the 911.3 reference agent through OUR field gate. The decisive control.

We beat the rule-based field 0.89-0.99 and score 0.55 on the ladder. The ladder
says the reference is 66 points STRONGER than us. So one of two things is true:

  ref scores >= our 0.89-0.99 here  -> the gate is merely saturated (no headroom),
                                       and its verdicts are uninformative but not wrong.
  ref scores BELOW us here          -> the gate is ANTI-correlated with ladder
                                       strength: beating these opponents is a
                                       different skill from beating the ladder,
                                       and every past FLAT/PASS verdict was noise
                                       around the wrong question.

Either way this is a fact about the measuring stick, not about a candidate, so it
does not depend on any of the broken comparisons.

Usage: uv run python gate_field_ref.py [--n 60] [--only mixed_ex1]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(WS, "exp083_scaleup"))

import gate_field as GF  # noqa: E402  (loads engine, decks, opponents)
import eval_raw as ER  # noqa: E402
from load_ref import make_ref_agent, DECK  # noqa: E402


def main():
    n = int(GF.arg("--n", "60"))
    only = GF.arg("--only", "")
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    opp_decks = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
    assert sorted(DECK) == sorted(grimm), "ref deck must equal ours for this to mean anything"

    opps = [o for o in GF.opponents(grimm, opp_decks) if not only or o[0] == only]
    print(f"REF(911.3) through the field gate, n={n} per matchup, seats alternated\n",
          flush=True)
    res, total = {}, 0.0
    t0 = time.time()
    for k, odeck, fac in opps:
        w, l, d, e = ER.run_matchup(
            None, list(grimm), list(odeck), fac, n,
            agent_factory=lambda _m, _my, _o: make_ref_agent())
        played = max(1, w + l + d)
        res[k] = (w / played, w, l, d, e)
        total += GF.WEIGHT[k] * (w / played)
        print(f"    {GF.LABEL[k]:<20} {w/played:.3f}  ({w}-{l}-{d}, err={e})", flush=True)
    if not only:
        print(f"\n  weighted {total/sum(GF.WEIGHT.values()):.3f}  ({time.time()-t0:.0f}s)")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"n": n, "res": res, "weight": GF.WEIGHT},
              open(os.path.join(HERE, "results", f"gate_ref_{only or 'all'}_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
