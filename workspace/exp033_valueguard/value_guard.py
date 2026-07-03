"""exp033 — VALUE-GUIDED opponent-reply search (Stage 2b) on the v012 pilot.

v013's guard vetoes only verified doom (ternary). This replaces the score with the
exp032 value net (pure numpy, mid-game AUC 0.773 on 99k self-play games): at MAIN
single-picks, roll out base + up to MAX_ALT candidate options through our turn +
the opponent's full reply (K belief determinizations, same as exp029), score the
end state with the value net (exact 1/0 at terminals), and switch to the best
candidate only when its mean value beats the base's by MARGIN (hedge vs value noise).

Env: GUARD_K (4), GUARD_MAX_ALT (8), VG_MARGIN (0.10), REVENGE_BONUS (50).
"""
from __future__ import annotations
import dataclasses
import os
import random
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp023_revenge"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
import revenge_policy as P  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
K = int(os.environ.get("GUARD_K", "4"))
MAX_ALT = int(os.environ.get("GUARD_MAX_ALT", "8"))
MARGIN = float(os.environ.get("VG_MARGIN", "0.10"))
ROLL_CAP = 120
STATS = {"checked": 0, "fired": 0, "errors": 0}

_NPZ = np.load(os.path.join(ROOT, "workspace", "exp032_valuescale", os.environ.get("VG_MLP", "value_mlp.npz")))
_W0, _b0, _W1, _b1, _W2, _b2 = (_NPZ[k] for k in ("W0", "b0", "W1", "b1", "W2", "b2"))
_MEAN, _STD = _NPZ["mean"], _NPZ["std"]


def _value_from_feats(f):
    z = (np.asarray(f, dtype=np.float64) - _MEAN) / _STD
    h = np.maximum(z @ _W0 + _b0, 0)
    h = np.maximum(h @ _W1 + _b1, 0)
    return float(1 / (1 + np.exp(-(h @ _W2 + _b2))[0]))


def _ene(mon):
    e = getattr(mon, "energyCards", None)
    if isinstance(e, list):
        return len(e)
    e = getattr(mon, "energies", None)
    return sum(e) if isinstance(e, list) else 0


def _feats(cur, my, first_player):
    me, opp = cur.players[my], cur.players[1 - my]

    def act_hp(p):
        a = p.active or []
        if a and a[0] is not None:
            mh = getattr(a[0], "maxHp", 0) or 0
            return (getattr(a[0], "hp", 0) / mh) if mh else 0.0
        return 0.0

    def act_ene(p):
        a = p.active or []
        return _ene(a[0]) if a and a[0] is not None else 0

    def board_ene(p):
        return sum(_ene(m) for m in list(p.active or []) + list(p.bench or []) if m is not None)

    def status(p):
        a = p.active or []
        if not (a and a[0] is not None):
            return 0
        return sum(int(bool(getattr(p, k, False))) for k in
                   ("asleep", "confused", "paralyzed", "poisoned", "burned"))

    pm, po = len(me.prize), len(opp.prize)
    return [po - pm, pm, po, act_hp(me), act_hp(opp), act_ene(me), act_ene(opp),
            board_ene(me), board_ene(opp), len(me.bench or []), len(opp.bench or []),
            me.handCount, opp.handCount, me.deckCount,
            cur.turn, int(first_player == my), status(opp)]


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _card_ids(cards):
    return [c.id for c in cards or [] if c is not None and getattr(c, "id", None) is not None]


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None) or [])
        out += _card_ids(getattr(m, "tools", None))
    return out


def make_agent(deck):
    base = P.make_agent(deck)
    roll = P.make_agent(deck)
    rng = random.Random(20260703)

    def det(me, opp):
        rem = Counter(deck)
        rem.subtract(Counter(_card_ids(me.hand) + _mon_ids(me.active)
                             + _mon_ids(me.bench) + _card_ids(me.discard)))
        pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
        if len(pool) < me.deckCount + len(me.prize):
            pool = list(deck)
        rng.shuffle(pool)
        opool = _mon_ids(opp.active) + _mon_ids(opp.bench) + _card_ids(opp.discard)
        if not opool:
            opool = list(deck)
        samp = lambda k: [opool[rng.randrange(len(opool))] for _ in range(k)]
        return dict(your_deck=pool[: me.deckCount],
                    your_prize=pool[me.deckCount: me.deckCount + len(me.prize)],
                    opponent_deck=samp(opp.deckCount),
                    opponent_prize=samp(len(opp.prize)),
                    opponent_hand=samp(opp.handCount),
                    opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])

    def rollout_value(obs, my, first_player, opt_i):
        """Apply opt_i, finish our turn, play opponent's reply; return end-state value."""
        me0 = obs.current.players[my]
        opp0 = obs.current.players[1 - my]
        ss = api.search_begin(obs, **det(me0, opp0))
        try:
            ss = api.search_step(ss.searchId, [opt_i])
            opp_seen = False
            for _ in range(ROLL_CAP):
                o = ss.observation
                cur = o.current
                if cur is not None and cur.result != -1:
                    return 1.0 if cur.result == my else 0.0
                if o.select is None or cur is None:
                    return None
                if cur.yourIndex == my:
                    if opp_seen:
                        break
                else:
                    opp_seen = True
                ss = api.search_step(ss.searchId,
                                     _clamp(roll(dataclasses.asdict(o)), o.select))
            o = ss.observation
            if o.current is None:
                return None
            return _value_from_feats(_feats(o.current, my, first_player))
        finally:
            try:
                api.search_release(ss.searchId)
            except Exception:
                try:
                    api.search_end()
                except Exception:
                    pass

    def mean_value(obs, my, fp, opt_i):
        vals = []
        for _ in range(K):
            v = rollout_value(obs, my, fp, opt_i)
            if v is None:
                return None
            vals.append(v)
        return sum(vals) / len(vals)

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            return list(deck)
        select = obs.select
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        if (select.maxCount != 1 or len(select.option) <= 1
                or select.context != api.SelectContext.MAIN):
            return base_sel
        try:
            my = obs.current.yourIndex
            fp = obs.current.firstPlayer
            STATS["checked"] += 1
            vb = mean_value(obs, my, fp, base_sel[0])
            if vb is None:
                return base_sel
            best_v, best_i = vb, base_sel[0]
            for i in range(min(len(select.option), MAX_ALT)):
                if i == base_sel[0]:
                    continue
                v = mean_value(obs, my, fp, i)
                if v is not None and v > best_v:
                    best_v, best_i = v, i
            if best_i != base_sel[0] and best_v >= vb + MARGIN:
                STATS["fired"] += 1
                return [best_i]
        except Exception:
            STATS["errors"] += 1
        return base_sel

    agent.__name__ = "value_guard"
    return agent
