"""exp014 M1: value calibration go/no-go.

Train a value net on top-ranker replay states (obs -> P(this player wins)) using
the REAL final outcome as the label, and evaluate on an episode-level holdout.
This is the decisive gate (PLAN.md M0/M1): if a value net can read the mid-game
prize race well (AUC >= 0.70), search has a real foundation -> continue RL.
If not, end the RL line honestly.

Features are the strategy-lens scalars the top-ranker analysis flagged as the
winning levers: the PRIZE RACE (prize differential) first, then board setup
(energized attacker) and engine uptime (hand/deck counts).

Usage:
  uv run python value_calib.py
"""
from __future__ import annotations
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
RECORDS = os.path.join(RESULTS, "records.jsonl")


# ---------- feature extraction ----------
FEATS = [
    "prize_diff", "prize_me", "prize_opp",      # prize race (core lever)
    "act_hp_me", "act_hp_opp",                  # active health ratio
    "act_ene_me", "act_ene_opp",                # energy on active (setup)
    "ene_board_me", "ene_board_opp",            # total energy on board
    "bench_me", "bench_opp",                    # development
    "hand_me", "hand_opp", "deck_me",           # engine uptime
    "turn", "going_first", "opp_status",        # tempo / position / disruption
]


def _ene_count(mon):
    ec = mon.get("energyCards")
    if isinstance(ec, list):
        return len(ec)
    en = mon.get("energies")
    return sum(en) if isinstance(en, list) else 0


def _board_energy(player):
    tot = 0
    for mon in (player.get("active") or []) + (player.get("bench") or []):
        if isinstance(mon, dict):
            tot += _ene_count(mon)
    return tot


def _act_hp(player):
    act = player.get("active") or []
    if act and isinstance(act[0], dict):
        mh = act[0].get("maxHp") or 0
        return (act[0].get("hp", 0) / mh) if mh else 0.0
    return 0.0


def _act_ene(player):
    act = player.get("active") or []
    return _ene_count(act[0]) if act and isinstance(act[0], dict) else 0


def _status(player):
    act = player.get("active") or []
    if not (act and isinstance(act[0], dict)):
        return 0
    return sum(int(bool(player.get(k))) for k in
               ("asleep", "confused", "paralyzed", "poisoned", "burned"))


def featurize(obs, ai):
    cur = obs.get("current", {})
    pls = cur.get("players", [])
    if ai >= len(pls):
        return None
    me, opp = pls[ai], pls[1 - ai]
    pm, po = len(me.get("prize", [])), len(opp.get("prize", []))
    return [
        po - pm, pm, po,
        _act_hp(me), _act_hp(opp),
        _act_ene(me), _act_ene(opp),
        _board_energy(me), _board_energy(opp),
        len(me.get("bench", [])), len(opp.get("bench", [])),
        me.get("handCount", 0), opp.get("handCount", 0), me.get("deckCount", 0),
        cur.get("turn", 0), int(cur.get("firstPlayer") == ai), _status(opp),
    ]


# ---------- metrics ----------
def auc(y, p):
    y = np.asarray(y); p = np.asarray(p)
    n1, n0 = y.sum(), (1 - y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    # average ranks for ties
    _, inv, cnt = np.unique(p, return_inverse=True, return_counts=True)
    csum = np.cumsum(cnt)
    avg = {i: (csum[i] - cnt[i] + 1 + csum[i]) / 2.0 for i in range(len(cnt))}
    ranks = np.array([avg[i] for i in inv])
    return (ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def brier(y, p):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def main():
    rows = []  # (feat, y, ep, step, holdout)
    ep_max = {}
    with open(RECORDS) as f:
        for line in f:
            r = json.loads(line)
            fv = featurize(r["obs"], r["ai"])
            if fv is None:
                continue
            y = 1 if r["reward"] == 1 else 0
            ep, step = r["ep"], r["step"]
            ep_max[ep] = max(ep_max.get(ep, 0), step)
            rows.append((fv, y, ep, step, r["holdout"]))
    print(f"loaded {len(rows)} feature rows over {len(ep_max)} episodes")

    X = np.array([r[0] for r in rows], dtype=np.float32)
    Y = np.array([r[1] for r in rows], dtype=np.float32)
    HO = np.array([r[4] for r in rows], dtype=bool)
    frac = np.array([rows[i][3] / max(ep_max[rows[i][2]], 1) for i in range(len(rows))])

    mu, sd = X[~HO].mean(0), X[~HO].std(0) + 1e-6
    Xn = (X - mu) / sd
    Xtr, Ytr = Xn[~HO], Y[~HO]
    Xte, Yte, fte = Xn[HO], Y[HO], frac[HO]
    print(f"train {len(Xtr)}  test {len(Xte)}  (test win-rate {Yte.mean():.3f})")

    import torch
    import torch.nn as nn
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        torch.zeros(1, device=dev)
    except Exception:
        dev = "cpu"
    print(f"device: {dev}")
    torch.manual_seed(0)

    net = nn.Sequential(nn.Linear(X.shape[1], 64), nn.ReLU(),
                        nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    lossf = nn.BCEWithLogitsLoss()
    xt = torch.tensor(Xtr, device=dev); yt = torch.tensor(Ytr, device=dev).view(-1, 1)
    xv = torch.tensor(Xte, device=dev)
    bs, n = 4096, len(xt)
    for ep in range(60):
        net.train(); perm = torch.randperm(n, device=dev)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            opt.zero_grad()
            loss = lossf(net(xt[idx]), yt[idx]); loss.backward(); opt.step()
    net.eval()
    with torch.no_grad():
        ptr = torch.sigmoid(net(xt)).cpu().numpy().ravel()
        pte = torch.sigmoid(net(xv)).cpu().numpy().ravel()

    # baseline: prize_diff alone (logistic via the standardized feature, monotone -> use raw)
    pdiff = X[HO, 0]  # prize_diff
    print("\n=== GO/NO-GO: value calibration on holdout ===")
    print(f" train AUC {auc(Ytr, ptr):.3f}   test AUC {auc(Yte, pte):.3f}")
    print(f" baseline AUC (prize_diff only): {auc(Yte, pdiff):.3f}")
    print(f" test accuracy@0.5: {np.mean((pte > 0.5) == Yte):.3f}   Brier: {brier(Yte, pte):.3f}")
    print("\n game-phase AUC (test):")
    for lo, hi in [(0, .25), (.25, .5), (.5, .75), (.75, 1.01)]:
        m = (fte >= lo) & (fte < hi)
        if m.sum() > 30:
            print(f"   phase [{lo:.2f},{hi:.2f}): n={int(m.sum()):5d}  AUC={auc(Yte[m], pte[m]):.3f}")
    mid = (fte >= 0.4) & (fte <= 0.6)
    mid_auc = auc(Yte[mid], pte[mid]) if mid.sum() > 30 else float("nan")
    print(f"\n *** MID-GAME AUC (phase 0.4-0.6, n={int(mid.sum())}): {mid_auc:.3f} ***")
    verdict = "GO (>=0.70)" if mid_auc >= 0.70 else "NO-GO (<0.70)"
    print(f" *** VERDICT: {verdict} ***")

    out = {"feats": FEATS, "test_auc": float(auc(Yte, pte)),
           "baseline_prize_auc": float(auc(Yte, pdiff)),
           "mid_game_auc": float(mid_auc), "brier": brier(Yte, pte),
           "test_acc": float(np.mean((pte > 0.5) == Yte)), "verdict": verdict,
           "n_train": int(len(Xtr)), "n_test": int(len(Xte))}
    json.dump(out, open(os.path.join(RESULTS, "value_calib.json"), "w"), indent=2)
    print(f"\n wrote results/value_calib.json")


if __name__ == "__main__":
    main()
