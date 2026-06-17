"""Build the v002 submission: lucario_v2 policy + belief-grounded PIMC search.

Self-contained main.py = the lucario_v2 rule policy (renamed _base_agent) plus a
belief-grounded PIMC wrapper with Conservative Override and a per-move time cap,
all crash-safe. Believed opponent deck = our own deck (Lucario-saturated ladder).

Outputs build/{main.py, deck.csv, cg/, submission.tar.gz}.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tarfile

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXP2_POLICIES = os.path.join(REPO, "workspace", "exp002_baselines", "policies")
CG_DIR = os.path.join(REPO, "data", "sim_sample", "cg")
BUILD = os.path.join(HERE, "build")

PIMC_BLOCK = r'''

# ===== belief-grounded PIMC wrapper (exp008 v002) =============================
import random as _random
import time as _time
import dataclasses as _dc
from cg.api import (search_begin as _sb, search_step as _ss, search_end as _se,
                    all_card_data as _acd, to_observation_class as _toc)

_PIMC_RNG = _random.Random(12345)
_CARD = {c.cardId: c for c in _acd()}
_BASICS = [cid for cid in my_deck if _CARD.get(cid) and _CARD[cid].basic]

# Tunables (validated in exp008: margin 0.10 recovers mirror, holds non-mirror).
_K = 6
_MAX_CAND = 4
_HORIZON = 40
_MARGIN = 0.10
_MOVE_BUDGET = 9.0   # seconds per decision; fall back to rule-based if exceeded
MAIN_SELECT = 0


def _legal(sel, select):
    n = len(select.option)
    sel = [i for i in sel if isinstance(i, int) and 0 <= i < n]
    sel = list(dict.fromkeys(sel))[:max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n))) if n else []
    return sel


def _sample(pool, k):
    if k <= 0:
        return []
    if k <= len(pool):
        return _PIMC_RNG.sample(pool, k)
    return [_PIMC_RNG.choice(pool) for _ in range(k)]


def _belief_det(obs):
    st = obs.current
    yi = st.yourIndex
    me, opp = st.players[yi], st.players[1 - yi]
    act = opp.active
    return dict(
        your_deck=_sample(list(my_deck), me.deckCount),
        your_prize=_sample(list(my_deck), len(me.prize)),
        opponent_deck=_sample(list(my_deck), opp.deckCount),
        opponent_prize=_sample(list(my_deck), len(opp.prize)),
        opponent_hand=_sample(list(my_deck), opp.handCount),
        opponent_active=[(_BASICS[0] if _BASICS else 1072)] if (len(act) > 0 and act[0] is None) else [],
    )


def _rollout(ss, my_index, deadline):
    for _ in range(_HORIZON):
        o = ss.observation
        st = o.current
        if st is not None and st.result != -1:
            return 1.0 if st.result == my_index else (0.5 if st.result == 2 else 0.0)
        if o.select is None:
            break
        try:
            sel = _legal(_base_agent(_dc.asdict(o)), o.select)
        except Exception:
            sel = _legal([0], o.select)
        ss = _ss(ss.searchId, sel)
        if _time.time() > deadline:
            break
    st = ss.observation.current
    me, opp = st.players[my_index], st.players[1 - my_index]
    v = 0.5 + 0.08 * (len(opp.prize) - len(me.prize))
    oa = sum(p.hp for p in opp.active if p)
    v -= 0.00008 * oa
    if not any(p for p in me.active):
        v -= 0.3
    return max(0.0, min(1.0, v))


def _pimc_choice(obs, obs_dict, t0):
    select = obs.select
    n = len(select.option)
    my_index = obs.current.yourIndex
    rb = _base_agent(obs_dict)
    rb0 = rb[0] if (rb and 0 <= rb[0] < n) else None
    cands = list(range(min(n, _MAX_CAND)))
    if rb0 is not None and rb0 not in cands:
        cands.append(rb0)
    deadline = t0 + _MOVE_BUDGET
    vals = {}
    for i in cands:
        if _time.time() > deadline:
            break
        tot = 0.0
        for _ in range(_K):
            det = _belief_det(obs)
            root = _sb(obs, **det)
            step = _ss(root.searchId, [i])
            tot += _rollout(step, my_index, deadline)
            _se()
        vals[i] = tot / _K
    if not vals or rb0 is None or rb0 not in vals:
        return rb if rb0 is not None else _legal([0], select)
    best = max(vals, key=vals.get)
    if best != rb0 and vals[best] >= vals[rb0] + _MARGIN:
        return [best]
    return [rb0]


def agent(obs_dict):
    """Crash-safe belief-PIMC agent. MAIN single-pick -> search; else rule-based."""
    try:
        obs = _toc(obs_dict)
    except Exception:
        if obs_dict.get("select") is None:
            return list(my_deck)
        return [0]
    if obs.select is None:
        return list(my_deck)
    select = obs.select
    try:
        if int(select.type) == MAIN_SELECT and select.maxCount == 1 and len(select.option) > 1:
            return _legal(_pimc_choice(obs, obs_dict, _time.time()), select)
        return _legal(_base_agent(obs_dict), select)
    except Exception:
        try:
            return _legal(_base_agent(obs_dict), select)
        except Exception:
            n = len(select.option)
            return list(range(min(max(1, select.minCount), n))) if n else []
'''


def build():
    src = open(os.path.join(EXP2_POLICIES, "lucario_v2.py")).read()
    src = re.sub(r"\bdef agent\(", "def _base_agent(", src)
    os.makedirs(BUILD, exist_ok=True)
    main_py = os.path.join(BUILD, "main.py")
    open(main_py, "w").write(src.rstrip() + "\n" + PIMC_BLOCK)

    deck = json.load(open(os.path.join(EXP2_POLICIES, "decks.json")))["lucario_v2"]
    assert len(deck) == 60
    open(os.path.join(BUILD, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")

    dst = os.path.join(BUILD, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

    tarp = os.path.join(BUILD, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(main_py, arcname="main.py")
        tar.add(os.path.join(BUILD, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))
    names = tarfile.open(tarp).getnames()
    assert {"main.py", "deck.csv", "cg/api.py", "cg/libcg.so"} <= set(names), names
    print("built", tarp)
    print("top-level:", sorted(n for n in names if "/" not in n), "files:", len(names))


if __name__ == "__main__":
    build()
