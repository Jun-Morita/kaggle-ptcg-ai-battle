"""Parity check: npmcts_policy.py's pure-python NpNet vs npnet.py's numpy NpNet,
on real recorded (enc/dec) samples. Run with cwd containing deck.csv (e.g.
build_np/) since npmcts_policy.py reads it at import.

Usage: cd build_np && uv run python ../parity_pure.py ../data/samples_turnbeam_w0.pkl 200
"""
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness")))
from harness import load_engine
load_engine()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import npnet
import npmcts_policy as PP

EI, EV, EO, DI, DV, DO, NC, CH, TURN, OUT, MU, GID = range(12)


def main():
    pkl_path = sys.argv[1] if len(sys.argv) > 1 else "../data/samples_turnbeam_w0.pkl"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    recs = pickle.load(open(pkl_path, "rb"))[:n]

    net_np = npnet.NpNet(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "pre2", "npnet.npz"))
    net_pp = PP.MODEL

    dv = dp = 0.0
    agree = 0
    t0 = time.time()
    for r in recs:
        nv, np_p = net_np.forward(r[EI], r[EV], r[EO], r[DI], r[DV], r[DO])
        np_p = np_p[:r[NC]]
        pv, pp_p = net_pp.forward(r[EI], r[EV], r[EO], r[DI], r[DV], r[DO])
        pp_p = pp_p[:r[NC]]
        dv = max(dv, abs(nv - pv))
        dp = max(dp, max(abs(a - b) for a, b in zip(np_p, pp_p)))
        agree += int(np_p.index(max(np_p)) == pp_p.index(max(pp_p)))
    dt = time.time() - t0
    print(f"n={len(recs)} max|dv|={dv:.2e} max|dp|={dp:.2e} argmax_agree={agree}/{len(recs)} "
          f"pure_python={dt/len(recs)*1000:.2f}ms/decision")


if __name__ == "__main__":
    main()
