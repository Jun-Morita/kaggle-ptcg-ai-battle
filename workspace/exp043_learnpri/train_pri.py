"""exp043 — train the search-priority model on Yushin's TO_HAND decisions.

Model (per candidate i with card id c_i):
    score_i = b[c_i] + W[c_i] . f_state + u . xf_i
    STOP    = b_stop + w_stop . f_state          (legal only when mn picks reached)
Sequential (Plackett-Luce) likelihood over the picked set, then STOP if they
voluntarily stopped below maxCount. Trained with torch (CPU is fine at this size),
exported as npz for pure-numpy inference inside the submission patch.

Game-level holdout: epid % 20 == 0 -> val (exp014 leakage lesson).

Usage: uv run python train_pri.py data/tohand.pkl results/pri1
"""
from __future__ import annotations
import os
import pickle
import sys

import numpy as np
import torch

DIM_F = 14
DIM_XF = 3


def load(path):
    recs = pickle.load(open(path, "rb"))
    cards = sorted({c for r in recs for c in r["cands"]})
    cix = {c: i for i, c in enumerate(cards)}
    tr, va = [], []
    for r in recs:
        (va if r["epid"] % 20 == 0 else tr).append(r)
    return recs, cards, cix, tr, va


class Pri(torch.nn.Module):
    def __init__(self, ncards):
        super().__init__()
        self.b = torch.nn.Parameter(torch.zeros(ncards))
        self.W = torch.nn.Parameter(torch.zeros(ncards, DIM_F))
        self.u = torch.nn.Parameter(torch.zeros(DIM_XF))
        self.b_stop = torch.nn.Parameter(torch.zeros(1))
        self.w_stop = torch.nn.Parameter(torch.zeros(DIM_F))

    def cand_scores(self, cidx, f, xf):
        return self.b[cidx] + (self.W[cidx] * f).sum(-1) + xf @ self.u

    def stop_score(self, f):
        return self.b_stop + f @ self.w_stop


def nll_of(model, r, cix):
    f = torch.tensor(r["feats"], dtype=torch.float32)
    cidx = torch.tensor([cix[c] for c in r["cands"]])
    xf = torch.tensor(r["cand_xf"], dtype=torch.float32)
    scores = model.cand_scores(cidx, f, xf)
    stop = model.stop_score(f)
    remaining = list(range(len(r["cands"])))
    taken = 0
    nll = 0.0
    for pick in r["picks"]:
        pool = scores[remaining]
        if taken >= r["min"]:
            pool = torch.cat([pool, stop])
        j = remaining.index(pick)
        nll = nll - torch.log_softmax(pool, 0)[j]
        remaining.remove(pick)
        taken += 1
    if taken < r["max"] and remaining and taken >= r["min"]:
        pool = torch.cat([scores[remaining], stop])
        nll = nll - torch.log_softmax(pool, 0)[-1]   # they chose to STOP
    return nll


def top1_acc(model, recs, cix):
    """First-pick accuracy (incl. predicting STOP when they took nothing)."""
    hit = tot = 0
    with torch.no_grad():
        for r in recs:
            f = torch.tensor(r["feats"], dtype=torch.float32)
            cidx = torch.tensor([cix[c] for c in r["cands"]])
            xf = torch.tensor(r["cand_xf"], dtype=torch.float32)
            scores = model.cand_scores(cidx, f, xf)
            if r["min"] == 0:
                scores = torch.cat([scores, model.stop_score(f)])
            pred = int(scores.argmax())
            truth = r["picks"][0] if r["picks"] else len(r["cands"])
            # semantic: same card name counts (different copy of same card id)
            if r["picks"] and pred < len(r["cands"]):
                hit += int(r["cands"][pred] == r["cands"][r["picks"][0]])
            else:
                hit += int(pred == truth)
            tot += 1
    return hit / max(tot, 1)


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/tohand.pkl"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "results/pri1"
    os.makedirs(out_dir, exist_ok=True)
    recs, cards, cix, tr, va = load(data_path)
    print(f"{len(recs)} decisions, {len(cards)} distinct cards, train {len(tr)} / val {len(va)}")

    # baseline: always pick the globally most-fetched card among candidates
    from collections import Counter
    freq = Counter()
    for r in tr:
        for p in r["picks"]:
            freq[r["cands"][p]] += 1
    hit = 0
    for r in va:
        best = max(range(len(r["cands"])), key=lambda i: freq.get(r["cands"][i], 0))
        hit += int(bool(r["picks"])) and int(r["cands"][best] == r["cands"][r["picks"][0]]) if r["picks"] else 0
    print(f"baseline (static most-fetched): val top-1 {hit / max(len(va), 1):.3f}")

    model = Pri(len(cards))
    opt = torch.optim.Adam(model.parameters(), lr=0.05, weight_decay=1e-4)
    rng = np.random.default_rng(0)
    for ep in range(30):
        order = rng.permutation(len(tr))
        tot = 0.0
        for start in range(0, len(order), 256):
            idx = order[start:start + 256]
            loss = sum(nll_of(model, tr[i], cix) for i in idx) / len(idx)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss) * len(idx)
        if ep % 3 == 2 or ep == 0:
            print(f"ep{ep:02d} train nll {tot / len(tr):.4f} | val top-1 {top1_acc(model, va, cix):.3f} "
                  f"(train top-1 {top1_acc(model, tr[:2000], cix):.3f})")

    np.savez(os.path.join(out_dir, "pri.npz"),
             cards=np.array(cards, dtype=np.int64),
             b=model.b.detach().numpy(), W=model.W.detach().numpy(),
             u=model.u.detach().numpy(),
             b_stop=model.b_stop.detach().numpy(), w_stop=model.w_stop.detach().numpy())
    print(f"saved {out_dir}/pri.npz  val top-1 {top1_acc(model, va, cix):.3f}")


if __name__ == "__main__":
    main()
