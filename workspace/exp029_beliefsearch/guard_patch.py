"""exp029 — PATCH_SRC for the v013 build: revenge patch (env-baked) + the
opponent-reply guard as self-contained source appended to the built main.py.

Build order (scripts/build_submission.py): lucario_v2 (agent->_base_agent) +
this PATCH_SRC + crash-safety wrapper. The guard captures the post-revenge
_base_agent as its inner policy and redefines _base_agent with the guard layer;
the safety wrapper then wraps the guarded agent. Uses only cg.api + stdlib.
GUARD_K env at build time (default 4).
"""
from __future__ import annotations
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_p = os.path.join(_ROOT, "workspace", "exp023_revenge")
if _p not in sys.path:
    sys.path.insert(0, _p)
import revenge_policy as RV

GUARD_K = int(os.environ.get("GUARD_K", "4"))

_GUARD = '''
# ===== opponent-reply guard (exp029 Stage 1) =====
import dataclasses as _g_dc
import random as _g_random
from collections import Counter as _g_Counter
from cg import api as _g_api

_G_K = __GUARD_K__
_G_MAX_ALT = 8
_G_ROLL_CAP = 120
_G_STATS = {"checked": 0, "doomed": 0, "fired": 0, "errors": 0}
_g_rng = _g_random.Random(20260702)
_g_inner = _base_agent          # post-revenge pilot: plays both seats in rollouts


def _g_clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _g_card_ids(cards):
    out = []
    for c in cards or []:
        cid = getattr(c, "id", None)
        if cid is not None:
            out.append(cid)
    return out


def _g_mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _g_card_ids([m])
        out += _g_card_ids(getattr(m, "preEvolution", None))
        out += _g_card_ids(getattr(m, "energyCards", None) or getattr(m, "energies", None))
        out += _g_card_ids(getattr(m, "tools", None))
    return out


def _g_max_energy(player):
    best = 0
    for m in list(player.active or []) + list(player.bench or []):
        if m is None:
            continue
        e = getattr(m, "energyCards", None) or getattr(m, "energies", None) or []
        best = max(best, len(e))
    return best


def _g_det(me, opp):
    rem = _g_Counter(my_deck)
    rem.subtract(_g_Counter(_g_card_ids(me.hand) + _g_mon_ids(me.active)
                            + _g_mon_ids(me.bench) + _g_card_ids(me.discard)))
    pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
    if len(pool) < me.deckCount + len(me.prize):
        pool = list(my_deck)
    _g_rng.shuffle(pool)
    opool = _g_mon_ids(opp.active) + _g_mon_ids(opp.bench) + _g_card_ids(opp.discard)
    if not opool:
        opool = list(my_deck)
    samp = lambda k: [opool[_g_rng.randrange(len(opool))] for _ in range(k)]
    return dict(your_deck=pool[: me.deckCount],
                your_prize=pool[me.deckCount: me.deckCount + len(me.prize)],
                opponent_deck=samp(opp.deckCount),
                opponent_prize=samp(len(opp.prize)),
                opponent_hand=samp(opp.handCount),
                opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])


def _g_reply_outcome(obs, my, opt_i):
    me0 = obs.current.players[my]
    opp0 = obs.current.players[1 - my]
    prizes0 = len(opp0.prize)
    charge0 = _g_max_energy(me0)
    ss = _g_api.search_begin(obs, **_g_det(me0, opp0))
    try:
        ss = _g_api.search_step(ss.searchId, [opt_i])
        phase_opp_seen = False
        for _ in range(_G_ROLL_CAP):
            o = ss.observation
            cur = o.current
            if cur is not None and cur.result != -1:
                return 2 if cur.result == (1 - my) else 0
            if o.select is None or cur is None:
                return None
            if cur.yourIndex == my:
                if phase_opp_seen:
                    break
            else:
                phase_opp_seen = True
            ss = _g_api.search_step(ss.searchId,
                                    _g_clamp(_g_inner(_g_dc.asdict(o)), o.select))
        o = ss.observation
        if o.current is None:
            return None
        me1 = o.current.players[my]
        opp1 = o.current.players[1 - my]
        if prizes0 - len(opp1.prize) >= 2:
            return 1
        if charge0 >= 2 and _g_max_energy(me1) < charge0 - 1:
            return 1
        return 0
    finally:
        try:
            _g_api.search_release(ss.searchId)
        except Exception:
            try:
                _g_api.search_end()
            except Exception:
                pass


def _g_doom_all_K(obs, my, opt_i):
    worst = 0
    for _ in range(_G_K):
        d = _g_reply_outcome(obs, my, opt_i)
        if d is None:
            return None
        if d == 0:
            return 0
        worst = max(worst, d)
    return worst


def _base_agent(obs_dict):
    sel_out = _g_inner(obs_dict)
    try:
        obs = to_observation_class(obs_dict)
        select = obs.select
        if (select is None or select.maxCount != 1 or len(select.option) <= 1
                or select.context != _g_api.SelectContext.MAIN):
            return sel_out
        base_sel = _g_clamp(sel_out, select)
        my = obs.current.yourIndex
        _G_STATS["checked"] += 1
        base_doom = _g_doom_all_K(obs, my, base_sel[0])
        if not base_doom:
            return sel_out
        _G_STATS["doomed"] += 1
        best = (base_doom, base_sel[0])
        for i in range(min(len(select.option), _G_MAX_ALT)):
            if i == base_sel[0]:
                continue
            d = _g_doom_all_K(obs, my, i)
            if d is not None and d < best[0]:
                best = (d, i)
                if d == 0:
                    break
        if best[1] != base_sel[0]:
            _G_STATS["fired"] += 1
            return [best[1]]
    except Exception:
        _G_STATS["errors"] += 1
    return sel_out
'''

PATCH_SRC = RV.PATCH_SRC + "\n" + _GUARD.replace("__GUARD_K__", str(GUARD_K))
