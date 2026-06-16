"""Greedy turn-rollout lookahead agent using the Search API.

At each of our decisions we, for every top-level option:
  1. search_step that option,
  2. greedily continue OUR turn with a cheap default policy until control leaves
     us (or the game ends),
  3. score the resulting state with a heuristic value V() from our perspective.
We then pick the option with the best V(). Hidden info is determinized like the
official MCTS sample. Any search failure falls back to a safe heuristic choice,
so the agent never crashes (stability matters for the ladder).

Exposes `make_lookahead_agent(deck, ...)` returning agent(obs_dict)->list[int].
"""
from __future__ import annotations

import os
import random
import sys

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
if EXP1 not in sys.path:
    sys.path.insert(0, EXP1)

from harness import load_engine  # noqa: E402

api, _ = load_engine()
to_obs = api.to_observation_class

# OptionType ids
PLAY, ATTACH, EVOLVE, ABILITY, DISCARD, RETREAT, ATTACK, END = 7, 8, 9, 10, 11, 12, 13, 14

# Priority for the cheap rollout policy: develop the board, then attack, end last.
ROLLOUT_PRIORITY = {EVOLVE: 0, ABILITY: 1, ATTACH: 2, PLAY: 3, ATTACK: 4,
                    RETREAT: 5, DISCARD: 6, END: 9}


def _safe_default(select) -> list[int]:
    """A legal selection without search: prefer a develop/attack option for MAIN,
    else take the first minCount options."""
    n = len(select.option)
    mn, mx = select.minCount, select.maxCount
    if mx >= 1 and mn <= 1 and int(select.type) == 0:  # MAIN: pick by priority (not END)
        ranked = sorted(range(n), key=lambda i: ROLLOUT_PRIORITY.get(int(select.option[i].type), 8))
        return [ranked[0]]
    if mn <= 0:
        return []
    return list(range(min(mn, n)))


def _value(state, my_index: int) -> float:
    """Heuristic value of a state from my_index's perspective. Higher = better."""
    if state.result != -1:
        if state.result == my_index:
            return 1e6
        if state.result == 2:
            return -1.0
        return -1e6
    me = state.players[my_index]
    opp = state.players[1 - my_index]
    my_prize_rem = len(me.prize)
    opp_prize_rem = len(opp.prize)
    # prizes taken: fewer of my prizes remaining = closer to winning
    prize_score = (opp_prize_rem - my_prize_rem) * 1000.0

    def board_hp(ps):
        return sum(p.hp for p in ps.active if p) + sum(p.hp for p in ps.bench)

    def count(ps):
        return sum(1 for p in ps.active if p) + len(ps.bench)

    hp_score = (board_hp(me) - board_hp(opp)) * 0.1
    # pressure: opponent's active low HP is good
    opp_active_hp = sum(p.hp for p in opp.active if p)
    pressure = -opp_active_hp * 0.2
    board_score = (count(me) - count(opp)) * 5.0
    # having an active Pokémon at all is essential (no active = you lose)
    have_active = 50.0 if any(p for p in me.active) else -200.0
    return prize_score + hp_score + pressure + board_score + have_active


def _rollout_then_value(search_id, first_select, my_index, max_follow=20, rollout=True):
    """Apply first_select; if rollout, greedily continue our turn; return V(end)."""
    ss = api.search_step(search_id, first_select)
    if not rollout:
        return _value(ss.observation.current, my_index)
    for _ in range(max_follow):
        o = ss.observation
        st = o.current
        if st is not None and st.result != -1:
            return _value(st, my_index)
        if o.select is None:
            return _value(st, my_index)
        if st.yourIndex != my_index:  # control left us; evaluate end-of-our-turn
            return _value(st, my_index)
        # greedy continuation
        sel = _rollout_choice(o.select)
        ss = api.search_step(ss.searchId, sel)
    return _value(ss.observation.current, my_index)


def _rollout_choice(select) -> list[int]:
    n = len(select.option)
    mn, mx = select.minCount, select.maxCount
    if int(select.type) == 0 and mn <= 1 <= mx:  # MAIN: priority, attack before end
        ranked = sorted(range(n), key=lambda i: ROLLOUT_PRIORITY.get(int(select.option[i].type), 8))
        return [ranked[0]]
    if mn <= 0:
        return []
    return list(range(min(mn, n)))


def _determinize(obs, my_deck: list[int]):
    st = obs.current
    yi = st.yourIndex
    me = st.players[yi]
    opp = st.players[1 - yi]
    pool = list(my_deck)
    active = opp.active
    opp_active = [1072] if (len(active) > 0 and active[0] is None) else []
    return dict(
        your_deck=random.sample(pool, me.deckCount) if me.deckCount <= len(pool) else pool[:me.deckCount],
        your_prize=random.sample(pool, len(me.prize)) if len(me.prize) <= len(pool) else pool[:len(me.prize)],
        opponent_deck=[1072] * opp.deckCount,
        opponent_prize=[1] * len(opp.prize),
        opponent_hand=[1] * opp.handCount,
        opponent_active=opp_active,
    )


def make_lookahead_agent(deck: list[int], max_options: int = 12, seed: int | None = None,
                         rollout: bool = True):
    rng = random.Random(seed)

    def agent(obs_dict: dict) -> list[int]:
        obs = to_obs(obs_dict)
        if obs.select is None:
            return list(deck)
        select = obs.select
        n = len(select.option)
        my_index = obs.current.yourIndex

        # Only single-pick decisions are searched; multi-select uses safe default.
        if select.maxCount != 1 or n <= 1:
            return _safe_default(select)

        try:
            det = _determinize(obs, deck)
            root = api.search_begin(obs, **det)
        except Exception:
            return _safe_default(select)

        best_i, best_v = None, -float("inf")
        order = list(range(n))
        if n > max_options:
            order = order[:max_options]  # cap for speed
        try:
            for i in order:
                v = _rollout_then_value(root.searchId, [i], my_index, rollout=rollout)
                if v > best_v:
                    best_v, best_i = v, i
        except Exception:
            api.search_end()
            return _safe_default(select)
        api.search_end()

        if best_i is None:
            return _safe_default(select)
        return [best_i]

    agent.__name__ = "agent_lookahead"
    return agent
