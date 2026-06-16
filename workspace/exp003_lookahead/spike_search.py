"""Spike: validate the Search API on a real mid-game state.

Drive a game with two baseline agents; at the first decision with >1 option for
player 0, run search_begin + search_step on each option and print the resulting
state so we understand how to read transitions (HP, prizes, result, KO).
"""
from __future__ import annotations

import os
import random
import sys

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
from baselines import make_policy_agent, DECKS  # noqa: E402

api, game = load_engine()
to_obs = api.to_observation_class


def determinize(obs, my_deck: list[int]):
    """Mimic the official MCTS sample's hidden-info filling (counts must match)."""
    st = obs.current
    yi = st.yourIndex
    me = st.players[yi]
    opp = st.players[1 - yi]
    active = opp.active
    pool = list(my_deck)
    your_deck = random.sample(pool, me.deckCount)
    your_prize = random.sample(pool, len(me.prize))
    opp_active = [1072] if (len(active) > 0 and active[0] is None) else []
    return dict(
        your_deck=your_deck,
        your_prize=your_prize,
        opponent_deck=[1072] * opp.deckCount,
        opponent_prize=[1] * len(opp.prize),
        opponent_hand=[1] * opp.handCount,
        opponent_active=opp_active,
    )


def board_summary(state, yi):
    me, opp = state.players[yi], state.players[1 - yi]
    def hp(ps):
        tot = sum(p.hp for p in ps.active if p) + sum(p.hp for p in ps.bench)
        return tot
    return (f"result={state.result} myPrize={len(me.prize)} oppPrize={len(opp.prize)} "
            f"myHP={hp(me)} oppHP={hp(opp)} myBench={len(me.bench)} oppBench={len(opp.bench)}")


def main():
    random.seed(0)
    a0 = make_policy_agent("lucario_v2")
    a1 = make_policy_agent("dragapult")
    deck0, deck1 = DECKS["lucario_v2"], DECKS["dragapult"]

    obs, sd = game.battle_start(deck0, deck1)
    print("battle started, errorPlayer", sd.errorPlayer)

    def rollout_state(search_id, first_select, max_follow=12):
        """Apply first_select, then auto-resolve follow-up selects (greedy first
        option, or END if available) to reach end of the action; return state."""
        ss = api.search_step(search_id, first_select)
        for _ in range(max_follow):
            ro = ss.observation
            if ro.current is not None and ro.current.result != -1:
                return ro.current
            if ro.select is None:
                return ro.current
            # stop once control returns to opponent (we only want our immediate effect)
            if ro.current.yourIndex != 0:
                return ro.current
            k = ro.select.minCount
            sel = list(range(k)) if k > 0 else []
            ss = api.search_step(ss.searchId, sel)
        return ss.observation.current

    shown = 0
    for step in range(600):
        o = to_obs(obs)
        if o.current is not None and o.current.result != -1:
            print("game ended at step", step, "result", o.current.result)
            break
        if o.select is None:
            break
        pi = o.current.yourIndex
        n = len(o.select.option)
        # target a MAIN decision (selectType 0) for player0 mid game with an ATTACK option
        opt_types = [int(opt.type) for opt in o.select.option]
        is_main = int(o.select.type) == 0
        has_attack = 13 in opt_types  # OptionType.ATTACK
        if pi == 0 and is_main and has_attack and o.current.turn >= 3 and o.select.maxCount == 1:
            print(f"\n[step {step}] MAIN decision turn={o.current.turn} options={n}")
            print("  option types:", opt_types)
            print("  current:", board_summary(o.current, 0))
            try:
                det = determinize(o, deck0)
                root = api.search_begin(o, **det)
                for i in range(n):
                    st = rollout_state(root.searchId, [i])
                    tag = "ATTACK" if opt_types[i] == 13 else f"type{opt_types[i]}"
                    print(f"    opt{i:2d} [{tag:7s}] -> {board_summary(st, 0)}")
                api.search_end()
            except Exception as e:
                print("  search error:", repr(e))
            shown += 1
            if shown >= 2:
                break
        agent = a0 if pi == 0 else a1
        obs = game.battle_select(agent(obs))

    game.battle_finish()
    print("\nspike done")


if __name__ == "__main__":
    main()
