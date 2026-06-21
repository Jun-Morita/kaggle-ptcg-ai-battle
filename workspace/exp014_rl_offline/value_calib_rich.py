"""exp014 M1 (rich): fairer value-calibration go/no-go with CARD-LEVEL features.

The scalar probe (value_calib.py) hit mid-game AUC 0.64 == prize_diff alone:
the 17 scalars carry no info beyond the prize count, so mid-game (small prize
gap) was near-unpredictable. But the replay obs actually exposes the acting
player's HAND CONTENTS (2985/3002 records) and both sides' BOARD card-ids -- the
real mid-game value signal (resources/threats). This probe adds learned card
embeddings over {my hand, my board, opp board} on top of the 17 scalars.

Decision (PLAN M1): mid-game AUC (phase 0.4-0.6) >= 0.70 -> GO. Else end RL line.

Usage: uv run python value_calib_rich.py
"""
from __future__ import annotations
import json
import os

import numpy as np
import value_calib as base  # reuse featurize(), auc(), brier()

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
RECORDS = os.path.join(RESULTS, "records.jsonl")
VOCAB = 1269          # max card id 1267 -> PAD = 1268
PAD = 1268
EMB = 24


def bag_ids(items):
    out = [c.get("id") for c in (items or []) if isinstance(c, dict)
           and isinstance(c.get("id"), int) and 0 <= c.get("id") < PAD]
    return out or [PAD]


def main():
    scal, hand, myb, opb = [], [], [], []
    Y, EP, STEP, HO = [], [], [], []
    ep_max = {}
    with open(RECORDS) as f:
        for line in f:
            r = json.loads(line)
            fv = base.featurize(r["obs"], r["ai"])
            if fv is None:
                continue
            cur = r["obs"]["current"]; pls = cur["players"]
            me, opp = pls[r["ai"]], pls[1 - r["ai"]]
            scal.append(fv)
            hand.append(bag_ids(me.get("hand")))
            myb.append(bag_ids((me.get("active") or []) + (me.get("bench") or [])))
            opb.append(bag_ids((opp.get("active") or []) + (opp.get("bench") or [])))
            Y.append(1 if r["reward"] == 1 else 0)
            EP.append(r["ep"]); STEP.append(r["step"]); HO.append(r["holdout"])
            ep_max[r["ep"]] = max(ep_max.get(r["ep"], 0), r["step"])
    n = len(Y)
    print(f"loaded {n} rows over {len(ep_max)} episodes")

    X = np.array(scal, dtype=np.float32)
    Y = np.array(Y, dtype=np.float32)
    HO = np.array(HO, dtype=bool)
    frac = np.array([STEP[i] / max(ep_max[EP[i]], 1) for i in range(n)])
    mu, sd = X[~HO].mean(0), X[~HO].std(0) + 1e-6
    Xn = ((X - mu) / sd).astype(np.float32)

    import torch
    import torch.nn as nn
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        torch.zeros(1, device=dev)
    except Exception:
        dev = "cpu"
    print(f"device: {dev}")
    torch.manual_seed(0)

    def packbag(bags, idx):
        flat, offs, o = [], [], 0
        for i in idx:
            offs.append(o); flat.extend(bags[i]); o += len(bags[i])
        return (torch.tensor(flat, dtype=torch.long, device=dev),
                torch.tensor(offs, dtype=torch.long, device=dev))

    class Net(nn.Module):
        def __init__(self, ns):
            super().__init__()
            self.emb_h = nn.EmbeddingBag(VOCAB, EMB, mode="mean")
            self.emb_b = nn.EmbeddingBag(VOCAB, EMB, mode="mean")
            self.emb_o = nn.EmbeddingBag(VOCAB, EMB, mode="mean")
            self.mlp = nn.Sequential(nn.Linear(ns + 3 * EMB, 128), nn.ReLU(),
                                     nn.Dropout(0.3), nn.Linear(128, 64), nn.ReLU(),
                                     nn.Linear(64, 1))

        def forward(self, xs, hb, bb, ob):
            h = self.emb_h(*hb); b = self.emb_b(*bb); o = self.emb_o(*ob)
            return self.mlp(torch.cat([xs, h, b, o], 1))

    net = Net(X.shape[1]).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    lossf = nn.BCEWithLogitsLoss()

    tr = np.where(~HO)[0]; te = np.where(HO)[0]
    Xt = torch.tensor(Xn, device=dev); Yt = torch.tensor(Y, device=dev).view(-1, 1)
    print(f"train {len(tr)}  test {len(te)}  (test win-rate {Y[te].mean():.3f})")
    bs = 4096
    for ep in range(80):
        net.train(); np.random.shuffle(tr)
        for i in range(0, len(tr), bs):
            idx = tr[i:i + bs]
            opt.zero_grad()
            out = net(Xt[idx], packbag(hand, idx), packbag(myb, idx), packbag(opb, idx))
            loss = lossf(out, Yt[idx]); loss.backward(); opt.step()

    def predict(idx):
        net.eval(); ps = []
        with torch.no_grad():
            for i in range(0, len(idx), bs):
                j = idx[i:i + bs]
                ps.append(torch.sigmoid(net(Xt[j], packbag(hand, j), packbag(myb, j),
                                            packbag(opb, j))).cpu().numpy().ravel())
        return np.concatenate(ps)

    ptr, pte = predict(tr), predict(te)
    Yte, fte = Y[te], frac[te]
    print("\n=== GO/NO-GO (rich card-level features) ===")
    print(f" train AUC {base.auc(Y[tr], ptr):.3f}   test AUC {base.auc(Yte, pte):.3f}")
    print(f" scalar-only baseline test AUC was 0.688 (prize_diff 0.688)")
    print(f" test acc@0.5 {np.mean((pte > 0.5) == Yte):.3f}   Brier {base.brier(Yte, pte):.3f}")
    print("\n game-phase AUC (test):")
    for lo, hi in [(0, .25), (.25, .5), (.5, .75), (.75, 1.01)]:
        m = (fte >= lo) & (fte < hi)
        if m.sum() > 30:
            print(f"   phase [{lo:.2f},{hi:.2f}): n={int(m.sum()):5d}  AUC={base.auc(Yte[m], pte[m]):.3f}")
    mid = (fte >= 0.4) & (fte <= 0.6)
    mid_auc = base.auc(Yte[mid], pte[mid]) if mid.sum() > 30 else float("nan")
    print(f"\n *** MID-GAME AUC (0.4-0.6, n={int(mid.sum())}): {mid_auc:.3f} ***")
    verdict = "GO (>=0.70)" if mid_auc >= 0.70 else "NO-GO (<0.70)"
    print(f" *** VERDICT: {verdict} ***")
    json.dump({"test_auc": float(base.auc(Yte, pte)), "mid_game_auc": float(mid_auc),
               "brier": base.brier(Yte, pte), "verdict": verdict, "rich": True},
              open(os.path.join(RESULTS, "value_calib_rich.json"), "w"), indent=2)
    print(" wrote results/value_calib_rich.json")


if __name__ == "__main__":
    main()
