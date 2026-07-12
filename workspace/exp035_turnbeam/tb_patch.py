"""exp035 — PATCH_SRC for the v014 build: revenge patch + turn-beam layer as
self-contained source for the built main.py.

Build order: lucario_v2 (agent->_base_agent) + this PATCH + crash-safety wrapper.
The beam captures the post-revenge _base_agent as its inner base/rollout policy and
redefines _base_agent with the verified-throughput override. Single-module caveat:
in-search rollouts call the same inner policy whose module globals carry cross-turn
state (revenge's _rev tracker) — we snapshot/restore _rev around each planning call
so imagined states never leak into real-game tracking. cg.api + stdlib only.
Env at build time: TB_K (2), TB_BEAM (5), TB_BRANCH (10), TB_MAXSTEPS (900).
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

_CFG = {k: int(os.environ.get(k, d)) for k, d in
        (("TB_K", 2), ("TB_BEAM", 5), ("TB_BRANCH", 10), ("TB_MAXSTEPS", 900))}

_TB = '''
# ===== turn-beam: verified full-turn sequencing (exp035) =====
import dataclasses as _tb_dc
import random as _tb_random
from collections import Counter as _tb_Counter
from cg import api as _tb_api

_TB_K = __TB_K__
_TB_BEAM = __TB_BEAM__
_TB_BRANCH = __TB_BRANCH__
_TB_MAXSTEPS = __TB_MAXSTEPS__
_TB_DMG_MIN = 30
_TB_STATS = {"planned": 0, "fired": 0, "errors": 0}
_tb_rng = _tb_random.Random(20260704)
_tb_inner = _base_agent

# ===== exp045 TB_VALUE: learned terminal evaluator replaces the damage tiebreak =====
# When enabled, outcome()'s SECOND key becomes int(1000*V(end-of-turn state)) from
# exp032/033's 17-feature value MLP (mid-game AUC 0.806) instead of raw damage
# dealt; the FIRST key (prizes taken this turn, +100 on win) is unchanged, so
# "take prizes when you can" is preserved and only no-prize-turn planning changes.
# This targets the exp044-diagnosed blind spot: the damage tiebreak prefers
# chipping a 320hp Dragapult ex over evolution-line denial / setup quality.
_TB_VALUE = __TB_VALUE__
if _TB_VALUE:
    import numpy as _tb_np
    _tb_vz = _tb_np.load(__TB_VALUE_NPZ__)
    _TB_DMG_MIN = __TB_VALUE_MARGIN__     # margin now in value-milliunits

    def _tb_value(cur, my):
        me, opp = cur.players[my], cur.players[1 - my]
        def _e(m):
            e = getattr(m, "energyCards", None)
            if isinstance(e, list):
                return len(e)
            e = getattr(m, "energies", None)
            return sum(e) if isinstance(e, list) else 0
        def _ahp(p):
            a = p.active or []
            if a and a[0] is not None:
                mh = getattr(a[0], "maxHp", 0) or 0
                return (getattr(a[0], "hp", 0) / mh) if mh else 0.0
            return 0.0
        def _aene(p):
            a = p.active or []
            return _e(a[0]) if a and a[0] is not None else 0
        def _bene(p):
            return sum(_e(m) for m in list(p.active or []) + list(p.bench or []) if m is not None)
        def _st(p):
            a = p.active or []
            if not (a and a[0] is not None):
                return 0
            return sum(int(bool(getattr(p, k, False))) for k in
                       ("asleep", "confused", "paralyzed", "poisoned", "burned"))
        pm, po = len(me.prize), len(opp.prize)
        f = [po - pm, pm, po, _ahp(me), _ahp(opp), _aene(me), _aene(opp),
             _bene(me), _bene(opp), len(me.bench or []), len(opp.bench or []),
             me.handCount, opp.handCount, me.deckCount,
             cur.turn, int(cur.firstPlayer == my), _st(opp)]
        z = (_tb_np.asarray(f, dtype=_tb_np.float64) - _tb_vz["mean"]) / _tb_vz["std"]
        h = _tb_np.maximum(z @ _tb_vz["W0"] + _tb_vz["b0"], 0)
        h = _tb_np.maximum(h @ _tb_vz["W1"] + _tb_vz["b1"], 0)
        return float(1 / (1 + _tb_np.exp(-(h @ _tb_vz["W2"] + _tb_vz["b2"])[0])))


def _tb_clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _tb_card_ids(cards):
    return [c.id for c in cards or [] if c is not None and getattr(c, "id", None) is not None]


def _tb_mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _tb_card_ids([m])
        out += _tb_card_ids(getattr(m, "preEvolution", None))
        out += _tb_card_ids(getattr(m, "energyCards", None) or [])
        out += _tb_card_ids(getattr(m, "tools", None))
    return out


def _tb_board_hp(p):
    tot = 0
    for m in list(p.active or []) + list(p.bench or []):
        if m is not None:
            tot += getattr(m, "hp", 0) or 0
    return tot


def _tb_det(me, opp):
    rem = _tb_Counter(my_deck)
    rem.subtract(_tb_Counter(_tb_card_ids(me.hand) + _tb_mon_ids(me.active)
                             + _tb_mon_ids(me.bench) + _tb_card_ids(me.discard)))
    pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
    if len(pool) < me.deckCount + len(me.prize):
        pool = list(my_deck)
    _tb_rng.shuffle(pool)
    opool = _tb_mon_ids(opp.active) + _tb_mon_ids(opp.bench) + _tb_card_ids(opp.discard)
    if not opool:
        opool = list(my_deck)
    samp = lambda k: [opool[_tb_rng.randrange(len(opool))] for _ in range(k)]
    return dict(your_deck=pool[: me.deckCount],
                your_prize=pool[me.deckCount: me.deckCount + len(me.prize)],
                opponent_deck=samp(opp.deckCount),
                opponent_prize=samp(len(opp.prize)),
                opponent_hand=samp(opp.handCount),
                opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])


def _tb_beam_once(obs, my):
    me0 = obs.current.players[my]
    opp0 = obs.current.players[1 - my]
    opp_prize0, opp_hp0 = len(opp0.prize), _tb_board_hp(opp0)
    root = _tb_api.search_begin(obs, **_tb_det(me0, opp0))
    steps = 0

    def outcome(ss):
        cur = ss.observation.current
        if cur is None:
            return (-1, 0)
        pz = opp_prize0 - len(cur.players[1 - my].prize)
        if _TB_VALUE:
            dmg = int(1000 * _tb_value(cur, my))
        else:
            dmg = max(0, opp_hp0 - _tb_board_hp(cur.players[1 - my]))
        if cur.result == my:
            pz += 100
        elif cur.result != -1:
            return (-1, 0)
        return (pz, dmg)

    try:
        # base line (post-revenge inner policy) within the same determinization
        ss = root
        for _ in range(40):
            o = ss.observation
            cur = o.current
            if cur is None or cur.result != -1 or o.select is None or cur.yourIndex != my:
                break
            try:
                ss = _tb_api.search_step(ss.searchId, _tb_clamp(_tb_inner(_tb_dc.asdict(o)), o.select))
            except Exception:
                break
        base_pz, base_dmg = outcome(ss)

        frontier = [(root, None, False)]
        best = {}
        for _depth in range(24):
            nxt = []
            for st, first, done in frontier:
                o = st.observation
                cur = o.current
                ended = (done or cur is None or cur.result != -1
                         or o.select is None or cur.yourIndex != my)
                if ended:
                    if first is not None:
                        pz = outcome(st)
                        if pz > best.get(first, (-1, 0)):
                            best[first] = pz
                    continue
                n = len(o.select.option)
                if o.select.maxCount != 1:
                    idxs = [_tb_clamp(list(range(o.select.minCount)), o.select)]
                else:
                    idxs = [[i] for i in range(min(n, _TB_BRANCH))]
                for sel in idxs:
                    if steps >= _TB_MAXSTEPS:
                        break
                    try:
                        child = _tb_api.search_step(st.searchId, sel)
                    except Exception:
                        continue
                    steps += 1
                    f = first if first is not None else (sel[0] if len(sel) == 1 else None)
                    nxt.append((child, f, False))
            if not nxt or steps >= _TB_MAXSTEPS:
                break
            nxt.sort(key=lambda t: outcome(t[0]), reverse=True)
            frontier = nxt[:_TB_BEAM]
        for st, first, _d in frontier:
            if first is not None and st.observation.current is not None:
                pz = outcome(st)
                if pz > best.get(first, (-1, 0)):
                    best[first] = pz
        return best, base_pz, base_dmg
    finally:
        try:
            _tb_api.search_end()
        except Exception:
            pass


def _base_agent(obs_dict):
    sel_out = _tb_inner(obs_dict)
    try:
        obs = to_observation_class(obs_dict)
        select = obs.select
        if (select is None or select.maxCount != 1 or len(select.option) <= 1
                or select.context != _tb_api.SelectContext.MAIN):
            return sel_out
        base_sel = _tb_clamp(sel_out, select)
        my = obs.current.yourIndex
        _TB_STATS["planned"] += 1
        _rev_save = dict(_rev)            # revenge cross-turn tracker: shield from
        try:                              # imagined states seen during search
            qualify = None
            for _ in range(_TB_K):
                b, base_pz, base_dmg = _tb_beam_once(obs, my)
                det_q = {}
                for a, (pz, dmg) in b.items():
                    if pz > base_pz or (pz == base_pz and dmg >= base_dmg + _TB_DMG_MIN):
                        det_q[a] = (pz - base_pz, dmg - base_dmg)
                if qualify is None:
                    qualify = det_q
                else:
                    qualify = {a: min(m, det_q[a]) for a, m in qualify.items() if a in det_q}
                if not qualify:
                    return base_sel
        finally:
            _rev.clear()
            _rev.update(_rev_save)
        if qualify:
            best_a = max(qualify, key=qualify.get)
            if best_a != base_sel[0]:
                _TB_STATS["fired"] += 1
                return [best_a]
    except Exception:
        _TB_STATS["errors"] += 1
    return sel_out
'''

for _k, _v in _CFG.items():
    _TB = _TB.replace(f"__{_k}__", str(_v))

# exp045 TB_VALUE substitutions (env-gated; TB_VALUE=0 leaves a dead `if 0:` branch
# whose body is never executed and whose numpy import never runs)
_TB_VALUE_NPZ = os.path.join(_ROOT, "workspace", "exp032_valuescale",
                             os.environ.get("TB_VALUE_NPZ", "value_mlp2.npz"))
_TB = (_TB
       .replace("__TB_VALUE__", str(int(os.environ.get("TB_VALUE", "0"))))
       .replace("__TB_VALUE_NPZ__", repr(_TB_VALUE_NPZ))
       .replace("__TB_VALUE_MARGIN__", str(int(os.environ.get("TB_VALUE_MARGIN", "20")))))

PATCH_SRC = RV.PATCH_SRC + "\n" + _TB
