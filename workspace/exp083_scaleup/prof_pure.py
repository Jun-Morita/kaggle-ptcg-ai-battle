"""exp083 item-3: where does the pure-python forward actually spend its time?

The ship path is capped at ~0.29s/act (d128/1+1). Any capacity increase needs
that headroom, so before optimising anything, measure which kernel dominates.
Usage: uv run python prof_pure.py <weights_pure.pkl> <records.pkl> [n]
"""
from __future__ import annotations
import cProfile, os, pickle, pstats, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
from harness import load_engine  # noqa: E402
load_engine()
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
import npmcts_policy as PP  # noqa: E402

pkl, recs_path = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
PP.MODEL = PP.NpNet(pkl)
recs = pickle.load(open(recs_path, "rb"))[:n]


def run():
    for r in recs:
        PP.MODEL.forward(r[0], r[1], r[2], r[3], r[4], r[5])


t0 = time.time(); run(); dt = time.time() - t0
print(f"baseline: {dt/len(recs)*1000:.1f} ms/decision  ({len(recs)} decisions, {dt:.1f}s)")
p = cProfile.Profile(); p.enable(); run(); p.disable()
pstats.Stats(p).sort_stats("tottime").print_stats(8)
