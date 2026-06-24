"""Train a listwise ranker to imitate tomatomato (behavior cloning).

score(state,option) MLP -> softmax over a decision's options -> NLL vs the expert's
chosen index. Reports held-out TOP-1 action-match (does it pick what the expert picked?)
vs the random baseline (1/avg_opts). High match => the knack is imitable; then bc_agent
wraps it and we measure ladder-style winrate vs the field.

Usage: uv run python bc_train.py
"""
from __future__ import annotations
import os

import numpy as np
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = "cuda" if torch.cuda.is_available() else "cpu"


class Ranker(nn.Module):
    def __init__(self, d, h=64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, h), nn.ReLU(), nn.Linear(h, h // 2),
                                 nn.ReLU(), nn.Linear(h // 2, 1))

    def forward(self, x):       # x: [n_opt, d] -> [n_opt] scores
        return self.net(x).squeeze(-1)


def main():
    d = np.load(os.path.join(HERE, "results", "bc_data.npz"))
    X, groups, y = d["X"], d["groups"], d["y"]
    # decision offsets
    offs = np.concatenate([[0], np.cumsum(groups)])
    n_dec = len(groups)
    rng = np.random.default_rng(0)
    perm = rng.permutation(n_dec)
    n_val = n_dec // 5
    val_set = set(perm[:n_val].tolist())

    Xt = torch.tensor(X, device=DEV)
    model = Ranker(X.shape[1]).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)

    train_ids = [i for i in range(n_dec) if i not in val_set]
    val_ids = [i for i in range(n_dec) if i in val_set]

    def batch_loss(ids, train=True):
        tot, correct, n = 0.0, 0, 0
        for i in ids:
            s, e = offs[i], offs[i + 1]
            sc = model(Xt[s:e])
            tgt = torch.tensor(int(y[i]), device=DEV)
            loss = nn.functional.cross_entropy(sc.unsqueeze(0), tgt.unsqueeze(0))
            if train:
                tot += loss
            else:
                tot += loss.item()
                correct += int(sc.argmax().item() == y[i])
                n += 1
        return (tot, correct, n)

    # baseline: random pick = mean(1/group_size) on val
    rand_acc = float(np.mean([1.0 / groups[i] for i in val_ids]))

    bs = 256
    for ep in range(40):
        model.train()
        rng.shuffle(train_ids)
        for b in range(0, len(train_ids), bs):
            opt.zero_grad()
            loss, _, _ = batch_loss(train_ids[b:b + bs], train=True)
            loss.backward()
            opt.step()
        if ep % 10 == 9 or ep == 0:
            model.eval()
            with torch.no_grad():
                _, ctr, n = batch_loss(val_ids, train=False)
                _, ctr_tr, n_tr = batch_loss(train_ids[:1000], train=False)
            print(f"ep{ep+1:2d} val top1={ctr/n:.3f}  train top1={ctr_tr/n_tr:.3f}  (random={rand_acc:.3f})")

    torch.save({"state": model.state_dict(), "d": X.shape[1]}, os.path.join(HERE, "results", "bc_model.pt"))
    print(f"\nsaved bc_model.pt | val action-match {ctr/n:.3f} vs random {rand_acc:.3f}")
    # per-option-count breakdown of accuracy (where does imitation help most?)


if __name__ == "__main__":
    main()
