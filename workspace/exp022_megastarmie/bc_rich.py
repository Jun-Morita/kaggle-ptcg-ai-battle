"""Richer-feature BC — the decisive representation test.

The k-NN experiment proved states identical in our 12-dim features had different expert
actions 58% of the time => the expert uses info we discard (hand contents, per-Mega energy
distribution). The info IS in the obs. Here we ENCODE it (hand card counts + board energy
distribution + opp detail) and re-run BC, watching the train/val gap (exp014 warned rich
features can overfit). If val action-match jumps well above 0.49 with train~=val, the
representation was the limiter and the user's "accumulate expert data -> RL" path is viable.

Usage: uv run python bc_rich.py
"""
from __future__ import annotations
import glob
import json
import os

import numpy as np
import torch
import torch.nn as nn

import bc_dataset as BD
import bc_train as BT

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# deck/key cards whose HAND presence drives sequencing
HAND_KEYS = [1030, 860, 1031, 861, 3, 1145, 1189, 1119, 1182, 1123, 1122, 1086,
             1229, 1227, 1252, 1097, 1225, 1211]


def rich_state(obs):
    base = BD.state_feats(obs)
    cur = obs["current"]
    yi = cur["yourIndex"]
    players = cur["players"]
    me = players[yi]
    opp = players[1 - yi] if len(players) > 1 else {}
    hand = me.get("hand") or []
    hand_ids = [c.get("id") for c in hand if isinstance(c, dict)]
    hc = np.array([hand_ids.count(k) for k in HAND_KEYS], dtype=np.float32) / 4.0
    board = (me.get("active") or []) + (me.get("bench") or [])
    megas = [p for p in board if p and p.get("id") in (BD.MSTARMIE, BD.MFROSLASS)]
    me_e = [len(p.get("energies", [])) for p in megas]
    dist = np.array([
        sum(1 for e in me_e if e == 0),
        sum(1 for e in me_e if e == 1),
        sum(1 for e in me_e if e == 2),
        sum(1 for e in me_e if e >= 3),
        (max(me_e) / 3.0) if me_e else 0.0,             # closest-to-attack signal
        sum(me_e) / 9.0,                                 # total energy on megas
        sum(1 for p in board if p and p.get("id") == BD.STARYU) / 4.0,
        sum(1 for p in board if p and p.get("id") == BD.SNORUNT) / 4.0,
        len(opp.get("bench") or []) / 5.0,
        opp.get("handCount", len(opp.get("hand") or [])) / 12.0,
    ], dtype=np.float32)
    return np.concatenate([base, hc, dist])


def build():
    files = sorted(glob.glob(os.path.join(BD.REPLAYS, "*.json")))
    X, groups, y = [], [], []
    for path in files:
        d = json.load(open(path))
        steps = d["steps"]
        idx = BD.starmie_idx(steps)
        for st in steps:
            ag = st[idx]
            obs = ag.get("observation")
            act = ag.get("action")
            if not isinstance(obs, dict) or not act:
                continue
            sel = obs.get("select")
            if not sel:
                continue
            opts = sel.get("option", [])
            if len(opts) < 2 or len(opts) == 60 or sel.get("context") != 0:
                continue
            if sel.get("maxCount") != 1 or len(act) != 1:
                continue
            chosen = act[0]
            if not (isinstance(chosen, int) and chosen < len(opts)):
                continue
            sf = rich_state(obs)
            X.extend(np.concatenate([sf, BD.option_feats(o, obs)]) for o in opts)
            groups.append(len(opts))
            y.append(chosen)
    return np.array(X, np.float32), np.array(groups, np.int32), np.array(y, np.int32)


def main():
    X, groups, y = build()
    print(f"rich dataset: decisions={len(groups)} rows={len(X)} feat_dim={X.shape[1]}")
    offs = np.concatenate([[0], np.cumsum(groups)])
    n = len(groups)
    rng = np.random.default_rng(0)
    perm = rng.permutation(n)
    val = set(perm[:n // 5].tolist())
    tr_ids = [i for i in range(n) if i not in val]
    val_ids = [i for i in range(n) if i in val]
    Xt = torch.tensor(X, device=DEV)
    model = BT.Ranker(X.shape[1], h=96).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=3e-5)
    rand_acc = float(np.mean([1.0 / groups[i] for i in val_ids]))

    def acc(ids):
        c = 0
        with torch.no_grad():
            for i in ids:
                s, e = offs[i], offs[i + 1]
                if model(Xt[s:e]).argmax().item() == y[i]:
                    c += 1
        return c / len(ids)

    for ep in range(50):
        model.train()
        rng.shuffle(tr_ids)
        for b in range(0, len(tr_ids), 256):
            opt.zero_grad()
            loss = 0.0
            for i in tr_ids[b:b + 256]:
                s, e = offs[i], offs[i + 1]
                loss = loss + nn.functional.cross_entropy(
                    model(Xt[s:e]).unsqueeze(0), torch.tensor(int(y[i]), device=DEV).unsqueeze(0))
            loss.backward()
            opt.step()
        if ep % 10 == 9:
            model.eval()
            print(f"ep{ep+1:2d} val={acc(val_ids):.3f} train={acc(tr_ids[:1200]):.3f} "
                  f"(lightweight MLP=0.49, random={rand_acc:.3f})")


if __name__ == "__main__":
    main()
