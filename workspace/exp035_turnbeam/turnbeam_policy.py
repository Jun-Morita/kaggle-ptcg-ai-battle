"""exp035 — TURN-BEAM planner: full-turn sequencing search on the v012 pilot.

Gap being attacked (exp022 take-when-legal + exp034 race math): our pilot picks
options greedily one at a time and never plans the TURN — tutor-chain order,
attach-Band-BEFORE-attack, keep-Postwick-up, evolve-then-attack. Top public agents
(LO 1083, metall 955, multiply 940) all ship some turn-level planning.

Mechanism: at MAIN single-pick decisions, for K determinizations fork the engine
search tree (search_step from a shared root is a fork) and BEAM-search to the end
of our turn — no Python policy calls inside the beam, options are expanded
exhaustively (capped) and states scored by plan arithmetic:
  win/loss >> prizes taken >> damage dealt >> attacker readiness (Trevenant count,
  energy, Band on board, Postwick up) >> hand/board development.
The first action of the best line (score summed across determinizations) is played
if it beats the base policy's choice; ties/failures fall back to base. Crash-safe.

Env: TB_K (2), TB_BEAM (5), TB_BRANCH (10), TB_MAXSTEPS (900), REVENGE_BONUS (50).
"""
from __future__ import annotations
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp023_revenge"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
import revenge_policy as P  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
K = int(os.environ.get("TB_K", "2"))
BEAM = int(os.environ.get("TB_BEAM", "5"))
BRANCH = int(os.environ.get("TB_BRANCH", "10"))
MAXSTEPS = int(os.environ.get("TB_MAXSTEPS", "900"))
STATS = {"planned": 0, "fired": 0, "bail": 0, "errors": 0}

_TREVENANT, _PHANTUMP = 879, 878
_BAND, _POSTWICK = 1171, 1255


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


def _board_hp(p):
    tot = 0
    for m in list(p.active or []) + list(p.bench or []):
        if m is not None:
            tot += getattr(m, "hp", 0) or 0
    return tot


def _eval(cur, my, opp_prize0, opp_hp0):
    """Plan-arithmetic score of a state from OUR pov (end/partial of our turn)."""
    if cur.result != -1:
        return 1e6 if cur.result == my else -1e6
    me, opp = cur.players[my], cur.players[1 - my]
    s = 12000.0 * (opp_prize0 - len(opp.prize))          # prizes taken this turn
    s += 8.0 * max(0, opp_hp0 - _board_hp(opp))          # damage dealt
    postwick = any(c is not None and getattr(c, "id", None) == _POSTWICK
                   for c in (cur.stadium or []))
    s += 150.0 * postwick
    trev = 0
    for j, m in enumerate(list(me.active or []) + list(me.bench or [])):
        if m is None:
            continue
        if m.id == _TREVENANT:
            trev += 1
            e = len(getattr(m, "energyCards", None) or [])
            s += 120.0 * min(e, 1)                       # armed attacker
            if any(getattr(t, "id", None) == _BAND for t in (getattr(m, "tools", None) or [])):
                s += 150.0 if j == 0 else 60.0           # Band, esp. on the active
        elif m.id == _PHANTUMP:
            s += 40.0
    s += 350.0 * trev
    s += 12.0 * me.handCount + 25.0 * len(me.bench or [])
    return s


def make_agent(deck):
    base = P.make_agent(deck)   # REAL decisions only — never call on search states
    roll = P.make_agent(deck)   # separate instance for in-search rollouts (its
                                # internal globals get corrupted by imagined states)
    rng = random.Random(20260704)

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

    import dataclasses as _dc

    def base_line_prizes(root, my, opp_prize0):
        """Roll the BASE policy to end of turn from the root fork; return prizes taken."""
        ss = root
        for _ in range(40):
            o = ss.observation
            cur = o.current
            if cur is None or cur.result != -1 or o.select is None or cur.yourIndex != my:
                break
            try:
                sel = _clamp(roll(_dc.asdict(o)), o.select)
                ss = api.search_step(ss.searchId, sel)
            except Exception:
                break
        cur = ss.observation.current
        if cur is None:
            return 0, 0, False
        won = cur.result == my
        return (opp_prize0 - len(cur.players[1 - my].prize),
                _board_hp(cur.players[1 - my]), won)

    def beam_once(obs, my):
        """One determinization: beam to end of our turn; return {first_action: best_score}."""
        me0 = obs.current.players[my]
        opp0 = obs.current.players[1 - my]
        opp_prize0, opp_hp0 = len(opp0.prize), _board_hp(opp0)
        root = api.search_begin(obs, **det(me0, opp0))
        steps = 0
        # frontier entries: (state, first_action, done)
        frontier = [(root, None, False)]
        best = {}

        def score_of(ss):
            return _eval(ss.observation.current, my, opp_prize0, opp_hp0)

        def prizes_of(ss):
            """(prizes_taken, damage_dealt) — lexicographic objective; loss = worst."""
            cur = ss.observation.current
            if cur is None:
                return (-1, 0)
            pz = opp_prize0 - len(cur.players[1 - my].prize)
            dmg = max(0, opp_hp0 - _board_hp(cur.players[1 - my]))
            if cur.result == my:
                pz += 100          # outright win dominates
            elif cur.result != -1:
                return (-1, 0)     # we lost during our own turn: never
            return (pz, dmg)

        base_pz, base_hp1, base_won = base_line_prizes(root, my, opp_prize0)
        if base_won:
            base_pz += 100
        base_dmg = max(0, opp_hp0 - base_hp1)
        try:
            for _depth in range(24):
                nxt = []
                for ss, first, done in frontier:
                    o = ss.observation
                    cur = o.current
                    ended = (done or cur is None or cur.result != -1
                             or o.select is None or cur.yourIndex != my)
                    if ended:
                        if first is not None:
                            pz = prizes_of(ss)
                            if pz > best.get(first, (-1, 0)):
                                best[first] = pz
                        continue
                    n = len(o.select.option)
                    if o.select.maxCount != 1:
                        # multi-pick mid-turn: delegate to a single legal default
                        idxs = [_clamp(list(range(o.select.minCount)), o.select)]
                    else:
                        idxs = [[i] for i in range(min(n, BRANCH))]
                    for sel in idxs:
                        if steps >= MAXSTEPS:
                            break
                        try:
                            child = api.search_step(ss.searchId, sel)
                        except Exception:
                            continue
                        steps += 1
                        f = first if first is not None else (sel[0] if len(sel) == 1 else None)
                        nxt.append((child, f, False))
                if not nxt or steps >= MAXSTEPS:
                    if steps >= MAXSTEPS:
                        STATS["bail"] += 1
                    break
                # prune to beam width by partial score
                nxt.sort(key=lambda t: score_of(t[0]), reverse=True)
                frontier = nxt[:BEAM]
            # flush remaining frontier as terminal-ish
            for ss, first, _d in frontier:
                if first is not None and ss.observation.current is not None:
                    pz = prizes_of(ss)
                    if pz > best.get(first, (-1, 0)):
                        best[first] = pz
        finally:
            try:
                api.search_end()
            except Exception:
                pass
        return best, base_pz, base_dmg

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
            STATS["planned"] += 1
            # verified-throughput override: a first action qualifies only if in EVERY
            # determinization its best line takes MORE prizes than the base line.
            qualify = None      # action -> min (prize_margin, dmg_margin) across dets
            DMG_MIN = 30
            for _ in range(K):
                b, base_pz, base_dmg = beam_once(obs, my)
                det_q = {}
                for a, (pz, dmg) in b.items():
                    if pz > base_pz or (pz == base_pz and dmg >= base_dmg + DMG_MIN):
                        det_q[a] = (pz - base_pz, dmg - base_dmg)
                if qualify is None:
                    qualify = det_q
                else:
                    qualify = {a: min(m, det_q[a]) for a, m in qualify.items() if a in det_q}
                if not qualify:
                    return base_sel
            if qualify:
                best_a = max(qualify, key=qualify.get)
                if best_a != base_sel[0]:
                    STATS["fired"] += 1
                    return [best_a]
        except Exception:
            STATS["errors"] += 1
        return base_sel

    agent.__name__ = "turnbeam"
    return agent
