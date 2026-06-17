"""Spike: does belief determinization + rule-based rollout produce realistic
opponent play inside the search? Compare to placeholder.

Drive a game to mid-game, then from a player-0 decision, run a full determinized
rollout with BOTH sides played by the rule-based policy, and report the outcome.
"""
from __future__ import annotations

import dataclasses
import os
import random
import sys

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
import baselines as B  # noqa: E402
from belief import belief_determinize  # noqa: E402

api, game = load_engine()
to_obs = api.to_observation_class


def placeholder_determinize(obs, rng):
    st = obs.current
    yi = st.yourIndex
    me, opp = st.players[yi], st.players[1 - yi]
    active = opp.active
    return dict(
        your_deck=[1072] * me.deckCount, your_prize=[1] * len(me.prize),
        opponent_deck=[1072] * opp.deckCount, opponent_prize=[1] * len(opp.prize),
        opponent_hand=[1] * opp.handCount,
        opponent_active=[1072] if len(active) > 0 and active[0] is None else [],
    )


def rollout(root_state, policy, my_index, horizon=200):
    """Play both sides with `policy` (rule-based) inside the search to terminal."""
    ss = root_state
    steps = 0
    opp_moves = 0
    for _ in range(horizon):
        o = ss.observation
        if o.current is not None and o.current.result != -1:
            return o.current.result, steps, opp_moves
        if o.select is None:
            return -1, steps, opp_moves
        d = dataclasses.asdict(o)
        sel = policy(d)
        # sanity-clamp
        n = len(o.select.option)
        sel = [i for i in sel if 0 <= i < n][:max(1, o.select.maxCount)] or list(range(min(o.select.minCount, n)))
        if o.current.yourIndex != my_index:
            opp_moves += 1
        ss = api.search_step(ss.searchId, sel)
        steps += 1
    return -1, steps, opp_moves


def main():
    rng = random.Random(0)
    a0 = B.make_policy_agent("lucario_v2")
    a1 = B.make_policy_agent("lucario_v2")
    deck = B.DECKS["lucario_v2"]
    obs, sd = game.battle_start(deck, deck)
    # drive to mid-game
    for _ in range(40):
        o = to_obs(obs)
        if o.current and o.current.result != -1:
            break
        pi = o.current.yourIndex
        obs = game.battle_select((a0 if pi == 0 else a1)(obs))
    o = to_obs(obs)
    print(f"mid-game: turn={o.current.turn} myPrize={len(o.current.players[0].prize)} "
          f"oppPrize={len(o.current.players[1].prize)}")

    policy = B.make_policy_agent("lucario_v2")  # rollout policy

    for label, det_fn in [("placeholder", lambda: placeholder_determinize(o, rng)),
                          ("belief", lambda: belief_determinize(o, deck, deck, rng))]:
        wins = []
        opp_total = 0
        for k in range(6):
            det = det_fn()
            try:
                root = api.search_begin(o, **det)
            except Exception as e:
                print(f"  [{label}] search_begin error: {e!r}")
                break
            res, steps, opp_moves = rollout(root, policy, my_index=0)
            api.search_end()
            wins.append(res)
            opp_total += opp_moves
        print(f"  [{label}] rollouts={len(wins)} results={wins} "
              f"avg_opp_moves={opp_total/max(len(wins),1):.0f}")

    game.battle_finish()
    print("spike done")


if __name__ == "__main__":
    main()
