"""exp015 v1: a tactical exact-search layer on top of v008 (router policy).

Within our own turn the game is near-perfect-information (the opponent does not
act and our hand is visible), so the engine's forward-search resolves KO/prize
events EXACTLY -- the near-terminal region exp014 showed is reliably readable
(late-game AUC 0.80). This layer, at each of our single-pick decisions, tries
each legal option one ply via the search API and measures the PRIZES it actually
takes (and whether it wins). If some option takes strictly more prizes (or wins)
than v008's choice, we switch to it; otherwise we defer to v008. Conservative
override => never worse than v008 (up to determinization of our own draws).

Crash-safe: any error falls back to v008's choice.
"""
from __future__ import annotations
import dataclasses
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp013_router")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
import router_policy as R  # noqa: E402

api, _ = load_engine()
to_obs = api.to_observation_class


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[:max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _my_turn_determinize(obs, my_deck, rng):
    """search_begin kwargs for OUR-turn search: our deck from the real decklist
    (plausible draws), opponent hidden = placeholder (they don't act this turn)."""
    st = obs.current
    yi = st.yourIndex
    me, opp = st.players[yi], st.players[1 - yi]

    def samp(pool, k):
        if k <= 0:
            return []
        return rng.sample(pool, k) if k <= len(pool) else [rng.choice(pool) for _ in range(k)]

    active = opp.active
    opp_active = [1072] if (len(active) > 0 and active[0] is None) else []
    return dict(
        your_deck=samp(list(my_deck), me.deckCount),
        your_prize=samp(list(my_deck), len(me.prize)),
        opponent_deck=[1072] * opp.deckCount,
        opponent_prize=[1] * len(opp.prize),
        opponent_hand=[1] * opp.handCount,
        opponent_active=opp_active,
    )


def _prizes_left(state, my_index):
    cur = state.observation.current
    if cur is None:
        return None, None
    me = cur.players[my_index]
    return len(me.prize), cur.result


def make_tactical_agent(deck, max_options=24, time_cap=2.0, seed=0):
    base = R.make_agent(deck)          # v008 policy (also handles deck-select)
    rng = random.Random(seed)

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            return list(deck)
        select = obs.select
        n = len(select.option)
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        # only single-pick decisions with a real choice are searchable for KO/prize
        if select.maxCount != 1 or n <= 1:
            return base_sel

        my_index = obs.current.yourIndex
        my_prize0 = len(obs.current.players[my_index].prize)
        base_i = base_sel[0] if base_sel else 0
        # LETHAL-ONLY: only worth searching when we are close enough to win this
        # turn (draw-robust, unambiguous). Greedy prize-max hurt the mirror (v1).
        if my_prize0 > 2:
            return base_sel

        try:
            # K-sample robust: a TRUE lethal wins across K independent
            # determinizations of our own draws (kills false positives that
            # hurt the mirror in the 1-sample version).
            K = 5

            def wins_robust(i):
                for _ in range(K):
                    det = _my_turn_determinize(obs, deck, rng)
                    root = api.search_begin(obs, **det)
                    ss = api.search_step(root.searchId, [i])
                    _, res = _prizes_left(ss, my_index)
                    api.search_end()
                    if res != my_index:
                        return False
                return True

            if wins_robust(base_i):       # v008 already takes the win
                return base_sel
            for i in range(min(n, max_options)):
                if i != base_i and wins_robust(i):   # v008 MISSED a true lethal
                    return [i]
        except Exception:
            try:
                api.search_end()
            except Exception:
                pass
            return base_sel
        return base_sel

    agent.__name__ = "tactical_v008"
    return agent
