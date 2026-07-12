"""Plan-B diagnostic -- measure the synthetic->real distribution gap BEFORE any
GPU training: top-1 agreement of a trained checkpoint (via the numpy port,
CPU-only) against v014's REAL ladder decisions (data/ladder_w9.pkl from
replay_to_records.py), split by opponent archetype.

Reading:
  - synthetic val top-1 reference: pre2 0.830 / dagger2 0.840 (oracle-free ==)
  - real-meta top-1 >> lower, especially on pool-absent archetypes (mixed_ex*,
    grimmsnarl-family) -> distribution gap CONFIRMED -> mixing the ladder corpus
    into pre3 has real headroom.
  - real-meta top-1 ~= synthetic -> gap is small; prioritize plan C instead.

Oracle handling: records carry the true opp_deck word (word index 22); we
evaluate BOTH with it (oracle) and with it stripped (oracle-free = ship
condition), mirroring pretrain.py's drop_oppdeck.

Usage: uv run python diag_realgap.py [npz_path] [pkl_path] [max_records]
"""
from __future__ import annotations
import os
import pickle
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import npnet  # numpy port, parity-verified vs torch

EI, EV, EO, DI, DV, DO, NC, CH, TURN, OUT, MU, GID = range(12)
OPPDECK_WORD = 22  # == pretrain.OPPDECK_WORD


def strip_oppdeck(ie, ve, oe):
    """Remove the opp_deck oracle word (verbatim pretrain.drop_oppdeck semantics)."""
    s, e = oe[OPPDECK_WORD], oe[OPPDECK_WORD + 1]
    if s == e:
        return ie, ve, oe
    cut = e - s
    return (ie[:s] + ie[e:], ve[:s] + ve[e:],
            [o if k <= OPPDECK_WORD else o - cut for k, o in enumerate(oe)])


def main():
    npz = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "pre2", "npnet.npz")
    pkl = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "data", "ladder_w9.pkl")
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 100000
    net = npnet.NpNet(npz)

    recs = []
    with open(pkl, "rb") as f:
        while len(recs) < cap:
            try:
                recs.extend(pickle.load(f))
            except EOFError:
                break
    recs = recs[:cap]
    print(f"model={os.path.relpath(npz, HERE)}  records={len(recs)}")

    hit = defaultdict(lambda: [0, 0, 0])   # mu -> [top1_oracle, top1_free, n]
    hit_multi = defaultdict(lambda: [0, 0, 0])
    for r in recs:
        _v, p = net.forward(r[EI], r[EV], r[EO], r[DI], r[DV], r[DO])
        pred_o = max(range(r[NC]), key=lambda i: p[i])
        ie, ve, oe = strip_oppdeck(r[EI], r[EV], r[EO])
        _v2, p2 = net.forward(ie, ve, oe, r[DI], r[DV], r[DO])
        pred_f = max(range(r[NC]), key=lambda i: p2[i])
        for d in (hit[r[MU]], hit["ALL"]):
            d[0] += pred_o == r[CH]; d[1] += pred_f == r[CH]; d[2] += 1
        if r[NC] > 1:
            for d in (hit_multi[r[MU]], hit_multi["ALL"]):
                d[0] += pred_o == r[CH]; d[1] += pred_f == r[CH]; d[2] += 1

    print(f"\n{'archetype':20s} {'n':>6s} {'top1(oracle)':>13s} {'top1(free)':>11s} {'multi-only(free)':>17s}")
    for mu in sorted(hit, key=lambda m: -hit[m][2]):
        o, fr, n = hit[mu]
        mo, mf, mn = hit_multi.get(mu, (0, 0, 0))
        print(f"{mu:20s} {n:6d} {o/n:13.3f} {fr/n:11.3f} {(mf/mn if mn else 0):17.3f}")


if __name__ == "__main__":
    main()
