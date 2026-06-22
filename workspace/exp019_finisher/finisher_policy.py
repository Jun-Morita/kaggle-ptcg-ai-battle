"""exp019: v009 (discipline) + a PRIZE-AWARE verified-lethal finisher.

exp015 (lethal forward-search) was a NO-GO because it determinized our deck by
random-sampling the full 60-card list, so the search "imagined" cards that were
actually PRIZED -> false-positive lethals that wrecked the move. The public Gold
Starmie agent fixes exactly this with prize tracking. Here we:

  base policy = v009 discipline (router + prize-liability patch);
  finisher    = at single-pick decisions when we are near lethal (my_prize<=2) AND
                the prize set is KNOWN, run K determinizations using the EXACT deck
                contents (decklist - visible - prized) and override base ONLY with an
                option that WINS in ALL K (a verified, draw-order-robust lethal).
  If the prize set is unknown or no verified win exists -> defer to v009. Crash-safe.

This makes the finisher upside-only: it can only switch to a move that truly wins.
"""
from __future__ import annotations
import dataclasses
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp013_router"),
          os.path.join(ROOT, "workspace", "exp018_adaptive"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
import discipline_policy as D  # noqa  (v009 base)
from prize_tracker import PrizeTracker  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
MAX_OPTIONS = 24
K = 5
PRIZE_GATE = 2          # only search when we are this close to winning
STATS = {"searched": 0, "known": 0, "fired": 0}   # diagnostics


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[:max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def make_agent(deck):
    base = D.make_agent(deck)            # v009 discipline
    tracker = PrizeTracker(deck)
    rng = random.Random(0)

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:           # new game / deck selection
            tracker.reset()
            return list(deck)
        try:
            tracker.update(obs)
        except Exception:
            pass
        select = obs.select
        n = len(select.option)
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        if select.maxCount != 1 or n <= 1:
            return base_sel

        my_index = obs.current.yourIndex
        my_prize0 = len(obs.current.players[my_index].prize)
        if my_prize0 > PRIZE_GATE:
            return base_sel
        STATS["searched"] += 1
        deck_contents = None
        prized = None
        try:
            deck_contents = tracker.deck_contents(obs)
            prized = tracker.prized()
        except Exception:
            deck_contents = None
        if deck_contents is None:        # prize set unknown -> conservative, trust v009
            return base_sel
        STATS["known"] += 1

        opp = obs.current.players[1 - my_index]
        prized_list = []
        for cid, cnt in (prized or {}).items():
            prized_list.extend([cid] * cnt)

        def det():
            d = list(deck_contents)
            rng.shuffle(d)
            active = opp.active
            opp_active = [1072] if (len(active) > 0 and active[0] is None) else []
            return dict(your_deck=d, your_prize=list(prized_list),
                        opponent_deck=[1072] * opp.deckCount,
                        opponent_prize=[1] * len(opp.prize),
                        opponent_hand=[1] * opp.handCount, opponent_active=opp_active)

        def _roll_to_result(ss, first_i):
            """Apply option first_i, then finish OUR turn with the base policy;
            return True iff the game resolves as a win for us this turn."""
            ss = api.search_step(ss.searchId, [first_i])
            for _ in range(40):
                o = ss.observation
                cur = o.current
                if cur is not None and cur.result != -1:
                    return cur.result == my_index
                if o.select is None or cur is None or cur.yourIndex != my_index:
                    return False                     # turn handed over -> no win this turn
                try:
                    sel = _clamp(base(dataclasses.asdict(o)), o.select)
                except Exception:
                    return False
                ss = api.search_step(ss.searchId, sel)
            return False

        def wins_all_K(i):
            for _ in range(K):
                root = api.search_begin(obs, **det())
                won = False
                try:
                    won = _roll_to_result(root, i)
                finally:
                    api.search_end()
                if not won:
                    return False
            return True

        try:
            base_i = base_sel[0] if base_sel else 0
            if wins_all_K(base_i):        # v009 already takes the verified win
                STATS["base_wins"] = STATS.get("base_wins", 0) + 1
                return base_sel
            STATS["any_opt_checked"] = STATS.get("any_opt_checked", 0) + 1
            for i in range(min(n, MAX_OPTIONS)):
                if i != base_i and wins_all_K(i):
                    STATS["fired"] += 1
                    return [i]            # verified lethal v009 missed
        except Exception:
            try:
                api.search_end()
            except Exception:
                pass
            return base_sel
        return base_sel

    agent.__name__ = "finisher_v010"
    return agent
