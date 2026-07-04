"""exp029 Stage 1 — opponent-reply guard (2-ply safety) on top of v012.

The greedy pilot never looks at what the opponent can do to the end-of-turn state
it leaves. This guard does, with the engine's exact forward search:

  at MAIN single-pick decisions, for the base policy's chosen option run K belief
  determinizations: apply the option, finish OUR turn with the base rules, then play
  the OPPONENT's whole reply turn with the same rules, and score the resulting state.
  Only when the base choice is DOOMED in all K (we lose / opponent takes >=2 prizes /
  our most-charged attacker is KO'd) do we look for an alternative option that avoids
  that doom in all K, and override. Otherwise defer to base. Crash-safe.

Determinization: our deck = PrizeTracker exact contents when known, else
decklist - visible (prize-blind but only used for OUR draw luck, not lethal claims);
opponent hidden zones = sampled from their own revealed cards (board + discard) +
the全カードプール fallback, so the reply is played with a plausible hand.

Env knobs: GUARD_K (default 4), GUARD_MAX_ALT (default 8).
"""
from __future__ import annotations
import dataclasses
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp019_finisher"),
          os.path.join(ROOT, "workspace", "exp023_revenge"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
_GB = os.environ.get("GUARD_BASE", "revenge")
if _GB == "exact":
    _p31 = os.path.join(ROOT, "workspace", "exp031_exactrev")
    if _p31 not in sys.path:
        sys.path.insert(0, _p31)
    import exact_policy as P  # noqa  (exp031 exact-window pilot)
elif _GB == "antispread":
    _p34 = os.path.join(ROOT, "workspace", "exp034_antispread")
    if _p34 not in sys.path:
        sys.path.insert(0, _p34)
    import antispread_policy as P  # noqa  (exp034 gated anti-dragapult discipline)
elif _GB == "turnbeam":
    _p35 = os.path.join(ROOT, "workspace", "exp035_turnbeam")
    if _p35 not in sys.path:
        sys.path.insert(0, _p35)
    import turnbeam_policy as P  # noqa  (exp035 verified turn-sequencing)
else:
    import revenge_policy as P  # noqa  (v012 pilot)
import revenge_policy as RVP  # rollout policy is ALWAYS the cheap plain pilot
from prize_tracker import PrizeTracker  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
K = int(os.environ.get("GUARD_K", "4"))
MAX_ALT = int(os.environ.get("GUARD_MAX_ALT", "8"))
ROLL_CAP = 120
STATS = {"checked": 0, "doomed": 0, "fired": 0, "errors": 0}


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _card_ids(cards):
    out = []
    for c in cards or []:
        cid = getattr(c, "id", None)
        if cid is not None:
            out.append(cid)
    return out


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None) or getattr(m, "energies", None))
        out += _card_ids(getattr(m, "tools", None))
    return out


def _max_energy(player):
    best = 0
    for m in list(player.active or []) + list(player.bench or []):
        if m is None:
            continue
        e = getattr(m, "energyCards", None) or getattr(m, "energies", None) or []
        best = max(best, len(e))
    return best


def make_agent(deck):
    base = P.make_agent(deck)
    roll_me = RVP.make_agent(deck)    # plays our seat inside the search (plain pilot:
    roll_opp = RVP.make_agent(deck)   # cheap + no beam recursion inside guard rollouts)
    tracker = PrizeTracker(deck)
    rng = random.Random(20260702)

    def our_deck_sample(me):
        rem = Counter(deck)
        rem.subtract(Counter(_card_ids(me.hand) + _mon_ids(me.active) + _mon_ids(me.bench)
                             + _card_ids(me.discard)))
        pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
        if len(pool) < me.deckCount + len(me.prize):
            pool = list(deck)
        rng.shuffle(pool)
        return pool[: me.deckCount], pool[me.deckCount: me.deckCount + len(me.prize)]

    def opp_pool(opp):
        seen = _mon_ids(opp.active) + _mon_ids(opp.bench) + _card_ids(opp.discard)
        return seen if seen else list(deck)

    def det(me, opp):
        d, prize = our_deck_sample(me)
        pool = opp_pool(opp)
        samp = lambda k: [pool[rng.randrange(len(pool))] for _ in range(k)]
        return dict(your_deck=d, your_prize=prize,
                    opponent_deck=samp(opp.deckCount),
                    opponent_prize=samp(len(opp.prize)),
                    opponent_hand=samp(opp.handCount),
                    opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])

    def reply_outcome(obs, my, opt_i):
        """Apply opt_i, finish our turn, play the opponent's reply turn.
        Returns doom level: 2 = we lose, 1 = opp takes >=2 prizes or KOs our most-
        charged attacker, 0 = fine. None on rollout failure (treated as unknown)."""
        me0 = obs.current.players[my]
        opp0 = obs.current.players[1 - my]
        prizes0 = len(opp0.prize)          # cards still face-down = prizes NOT yet taken
        charge0 = _max_energy(me0)
        ss = api.search_begin(obs, **det(me0, opp0))
        try:
            ss = api.search_step(ss.searchId, [opt_i])
            phase_opp_seen = False
            for _ in range(ROLL_CAP):
                o = ss.observation
                cur = o.current
                if cur is not None and cur.result != -1:
                    return 2 if cur.result == (1 - my) else 0
                if o.select is None or cur is None:
                    return None
                if cur.yourIndex == my:
                    if phase_opp_seen:      # opponent's reply turn is over
                        break
                    pol = roll_me
                else:
                    phase_opp_seen = True
                    pol = roll_opp
                ss = api.search_step(ss.searchId, _clamp(pol(dataclasses.asdict(o)), o.select))
            o = ss.observation
            if o.current is None:
                return None
            me1 = o.current.players[my]
            opp1 = o.current.players[1 - my]
            taken = prizes0 - len(opp1.prize)
            if taken >= 2:
                return 1
            if charge0 >= 2 and _max_energy(me1) < charge0 - 1:
                return 1                     # our charged attacker got wiped
            return 0
        finally:
            try:
                api.search_release(ss.searchId)
            except Exception:
                try:
                    api.search_end()
                except Exception:
                    pass

    def doom_all_K(obs, my, opt_i):
        worst = 0
        for _ in range(K):
            d = reply_outcome(obs, my, opt_i)
            if d is None:
                return None                  # can't verify -> don't act on it
            if d == 0:
                return 0                     # one safe world = not doomed
            worst = max(worst, d)
        return worst

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            tracker.reset()
            return list(deck)
        try:
            tracker.update(obs)
        except Exception:
            pass
        select = obs.select
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        ctx = getattr(select, "context", None)
        if select.maxCount != 1 or len(select.option) <= 1 or ctx != api.SelectContext.MAIN:
            return base_sel
        try:
            my = obs.current.yourIndex
            STATS["checked"] += 1
            base_doom = doom_all_K(obs, my, base_sel[0])
            if not base_doom:                # safe in some world, or unverifiable
                return base_sel
            STATS["doomed"] += 1
            best = (base_doom, base_sel[0])
            for i in range(min(len(select.option), MAX_ALT)):
                if i == base_sel[0]:
                    continue
                d = doom_all_K(obs, my, i)
                if d is not None and d < best[0]:
                    best = (d, i)
                    if d == 0:
                        break
            if best[1] != base_sel[0]:
                STATS["fired"] += 1
                return [best[1]]
        except Exception:
            STATS["errors"] += 1
        return base_sel

    agent.__name__ = "guard_v013"
    return agent
