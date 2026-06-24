"""Behavior-cloning dataset from tomatomato's 183 Mega-Starmie replays.

For every MAIN-context decision the expert made, emit:
  - per-option feature vectors (one row per candidate option)
  - the index of the option the expert actually chose (label)
A listwise ranker then learns score(state,option); the agent picks argmax.

This tests whether IMITATION captures the sequential/contextual piloting knack that
static heuristics (exp022 pilot1-3, all < generic) and self-play RL (exp004/008/010/014,
placeholder-opponent value net can't read mid-game) both fail to express.

Output: results/bc_data.npz  (X [N_opt, F], group [N_dec] sizes, y [N_dec] chosen-pos,
                              meta for opp archetype). Usage: uv run python bc_dataset.py
"""
from __future__ import annotations
import csv
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REPLAYS = os.path.join(ROOT, "references", "raw", "replays", "top_tomatomato_0624")

MSTARMIE, MFROSLASS, STARYU, SNORUNT = 1031, 861, 1030, 860
CRUSTLE, DWEBBLE = 345, 344
JETTING, NEBULA, RESENTFUL, ABS_SNOW = 1487, 1488, 1240, 1241
# OptionType ids
T_NUMBER, T_YES, T_NO, T_CARD, T_TOOL, T_ECARD, T_ENERGY = 0, 1, 2, 3, 4, 5, 6
T_PLAY, T_ATTACH, T_EVOLVE, T_ABILITY, T_DISCARD, T_RETREAT, T_ATTACK, T_END = 7, 8, 9, 10, 11, 12, 13, 14
TYPE_SLOTS = [T_PLAY, T_ATTACH, T_EVOLVE, T_ATTACK, T_RETREAT, T_END, T_ABILITY, T_CARD]


def card_info():
    hp, stage, isex = {}, {}, {}
    with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
        for row in csv.DictReader(f):
            try:
                cid = int(row["Card ID"])
            except (ValueError, KeyError):
                continue
            try:
                hp[cid] = int(row["HP"])
            except (ValueError, KeyError, TypeError):
                hp[cid] = 0
            stage[cid] = row.get("Stage (Pokémon)/Type (Energy and Trainer)", "")
            isex[cid] = "ex" in (row.get("Card Name", "") or "").lower()
    return hp, stage, isex


HP, STAGE, ISEX = card_info()


def pkmn_at(player, area, index):
    """area: 4=ACTIVE 5=BENCH. Return the pokemon dict or None."""
    if area == 4:
        a = player.get("active") or []
        return a[0] if a else None
    if area == 5:
        b = player.get("bench") or []
        return b[index] if index < len(b) else None
    return None


def opp_active(players, yi):
    o = players[1 - yi] if len(players) > 1 else {}
    a = o.get("active") or []
    return a[0] if a else None


def state_feats(obs):
    cur = obs["current"]
    yi = cur["yourIndex"]
    players = cur["players"]
    me = players[yi]
    act = (me.get("active") or [None])[0]
    board = (me.get("active") or []) + (me.get("bench") or [])
    n_mega = sum(1 for p in board if p and p.get("id") in (MSTARMIE, MFROSLASS))
    n_basic = sum(1 for p in board if p and p.get("id") in (STARYU, SNORUNT))
    oa = opp_active(players, yi)
    return np.array([
        cur.get("turn", 0) / 20.0,
        len(me.get("prize") or []) / 6.0,
        len((players[1 - yi].get("prize") or [])) / 6.0,
        me.get("handCount", len(me.get("hand") or [])) / 12.0,
        1.0 if cur.get("energyAttached") else 0.0,
        n_mega / 3.0,
        n_basic / 4.0,
        (len(act.get("energies", [])) / 3.0) if act else 0.0,
        1.0 if (act and act.get("id") in (MSTARMIE, MFROSLASS)) else 0.0,
        ((HP.get(oa.get("id"), 0) - oa.get("damage", 0)) / 330.0) if oa else 0.0,
        1.0 if (oa and oa.get("id") in (CRUSTLE, DWEBBLE)) else 0.0,   # wall flag
        1.0 if (oa and ISEX.get(oa.get("id"))) else 0.0,              # opp ex flag
    ], dtype=np.float32)


def option_feats(o, obs):
    cur = obs["current"]
    yi = cur["yourIndex"]
    me = cur["players"][yi]
    t = o.get("type")
    f = [1.0 if t == s else 0.0 for s in TYPE_SLOTS]          # 8 type one-hot
    aid = o.get("attackId")
    f += [1.0 if aid == JETTING else 0.0,
          1.0 if aid == NEBULA else 0.0,
          1.0 if aid in (RESENTFUL, ABS_SNOW) else 0.0]
    # target pokemon (for ATTACH/EVOLVE)
    tgt = None
    if t in (T_ATTACH, T_EVOLVE):
        tgt = pkmn_at(me, o.get("inPlayArea"), o.get("inPlayIndex", 0))
    te = len(tgt.get("energies", [])) if tgt else 0
    f += [
        1.0 if (o.get("inPlayArea") == 4) else 0.0,               # acts on active
        te / 3.0,                                                  # target energy count
        1.0 if (tgt and tgt.get("id") in (MSTARMIE, MFROSLASS)) else 0.0,  # target is mega
        1.0 if (tgt and tgt.get("id") in (STARYU, SNORUNT)) else 0.0,      # target is basic line
        1.0 if (t == T_ATTACH and tgt and tgt.get("id") == MSTARMIE and te == 2) else 0.0,  # finishing 3rd energy on Starmie
    ]
    return np.array(f, dtype=np.float32)


def starmie_idx(steps):
    idx = 0
    for st in steps:
        for i in (0, 1):
            a = st[i].get("action")
            if isinstance(a, list) and len(a) == 60 and (MSTARMIE in a or MFROSLASS in a):
                idx = i
    return idx


def main():
    files = sorted(glob.glob(os.path.join(REPLAYS, "*.json")))
    X, groups, y = [], [], []
    n_dec = 0
    for path in files:
        d = json.load(open(path))
        steps = d["steps"]
        idx = starmie_idx(steps)
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
            # core single-pick MAIN decisions with a real choice
            if len(opts) < 2 or len(opts) == 60:
                continue
            if sel.get("context") != 0:   # MAIN only (the piloting decisions)
                continue
            if sel.get("maxCount") != 1 or not isinstance(act, list) or len(act) != 1:
                continue
            chosen = act[0]
            if not (isinstance(chosen, int) and chosen < len(opts)):
                continue
            sf = state_feats(obs)
            rows = [np.concatenate([sf, option_feats(o, obs)]) for o in opts]
            X.extend(rows)
            groups.append(len(opts))
            y.append(chosen)
            n_dec += 1
    X = np.array(X, dtype=np.float32)
    groups = np.array(groups, dtype=np.int32)
    y = np.array(y, dtype=np.int32)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out = os.path.join(HERE, "results", "bc_data.npz")
    np.savez(out, X=X, groups=groups, y=y)
    print(f"decisions={n_dec}  option-rows={len(X)}  feat_dim={X.shape[1]}  avg_opts={len(X)/max(1,n_dec):.1f}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
