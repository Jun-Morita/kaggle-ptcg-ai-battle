"""exp083 re-ship -- NUMPY-FREE build of the d128 control net (sc083_d128ctl).

v042 shipped the big d256 net behind `try: import numpy` and Kaggle returned
"Validation Episode failed" -- the SAME error v015 got in 2026-07-09, whose
recorded root cause (see npmcts_policy.py's header and export_pure.py's) is that
the agent sandbox cannot run our numpy path. The try/except did not save us: the
validation replay shows both agents ERROR after 1.33s of agent time (overage
600 -> 598.67), i.e. the process died rather than raising a catchable exception.

So this build goes back to the only ship path with a clean record: the pure-stdlib
net, byte-identical code (npmcts_policy.py), same d128/h2/1+1 arch, same ~51MB
weight file -- ONLY the weights change, to the control run that got the same
training budget that lifted A3 (lr 1e-4 + warmup + clip + cosine, 24 epochs):
held-out oracle-free top-1 0.6238 -> 0.6577 (vs-Alakazam 0.6267 -> 0.6745).

Usage: uv run python build_pure.py [--n 20]
"""
from __future__ import annotations
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))

import build_np_submission as BNS  # noqa: E402

BNS.DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")
BNS.WEIGHTS_SRC = os.path.join(WS, "exp041_pilotnet", "results",
                               "sc083_d128ctl", "weights_pure.pkl")
BNS.OUT = os.path.join(HERE, "build_pure")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    assert os.path.exists(BNS.WEIGHTS_SRC), BNS.WEIGHTS_SRC
    print(f"deck={BNS.DECK}\nweights={BNS.WEIGHTS_SRC}\nout={BNS.OUT}\n")
    tarp = BNS.build()
    BNS.smoke(tarp, a.n)
