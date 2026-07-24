"""exp080 ship build -- the 5-day Grimmsnarl BC net as a numpy-free submission.

Reuses exp041/build_np_submission.py's build()+smoke() verbatim (main.py =
npmcts_policy.py with SEARCH_COUNT=0 = the exact pure-argmax/oracle-free policy
the kill-gate measured; raw_agent() hardcodes opp_deck=None so no mirror-guess
oracle word is fed). Only three inputs change: the Grimmsnarl deck, the
pre_grimm5 weights, and the output dir.

Usage: uv run python build_grimm.py [--n 20]
"""
from __future__ import annotations
import os, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))

import build_np_submission as BNS  # noqa: E402

BNS.DECK = os.path.join(HERE, "grimmsnarl_deck.json")
BNS.WEIGHTS_SRC = os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm10", "weights_pure.pkl")
BNS.OUT = os.path.join(HERE, "build_grimm10")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()
    assert os.path.exists(BNS.WEIGHTS_SRC), BNS.WEIGHTS_SRC
    print(f"deck={BNS.DECK}\nweights={BNS.WEIGHTS_SRC}\nout={BNS.OUT}\n")
    tarp = BNS.build()
    BNS.smoke(tarp, args.n)
