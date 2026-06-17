"""PIMC (Perfect-Information Monte Carlo) agent with belief determinization.

At a MAIN decision, for each candidate option we run K belief-determinized
rollouts where BOTH sides are played by the rule-based policy, and pick the
option with the best rollout win rate. All other (forced/trivial) decisions defer
to the rule-based policy. Any error falls back to the rule-based choice, so the
agent stays crash-safe.

This directly tests pillar A: does grounding the opponent in a real believed
deck (instead of placeholders) turn search from harmful (exp004 0.23) into
helpful (> rule-based 0.68)?
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

api, _ = load_engine()
to_obs = api.to_observation_class
MAIN = 0


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[:max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _rollout(root_state, pol_me, pol_opp, my_index, horizon):
    ss = root_state
    for _ in range(horizon):
        o = ss.observation
        if o.current is not None and o.current.result != -1:
            r = o.current.result
            return 1.0 if r == my_index else (0.0 if r == 1 - my_index else 0.5)
        if o.select is None:
            break
        pol = pol_me if o.current.yourIndex == my_index else pol_opp
        try:
            sel = _clamp(pol(dataclasses.asdict(o)), o.select)
        except Exception:
            sel = _clamp([0], o.select)
        ss = api.search_step(ss.searchId, sel)
    # horizon hit: heuristic in ~[0,1], prize race dominant + board pressure.
    st = ss.observation.current
    me, opp = st.players[my_index], st.players[1 - my_index]
    v = 0.5 + 0.08 * (len(opp.prize) - len(me.prize))

    def bhp(ps):
        return sum(p.hp for p in ps.active if p) + sum(p.hp for p in ps.bench)
    v += 0.00005 * (bhp(me) - bhp(opp))
    opp_act = sum(p.hp for p in opp.active if p)
    v -= 0.00008 * opp_act                      # pressure on their active
    if not any(p for p in me.active):
        v -= 0.3                                 # no active = nearly lost
    return max(0.0, min(1.0, v))


def _placeholder_determinize(obs, *_a, **_k):
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


def make_pimc_agent(my_deck, opp_deck=None, k_rollouts=6, max_candidates=6,
                    horizon=300, seed=0, use_belief=True, margin=0.0):
    """opp_deck: believed opponent decklist (oracle for the proof). Defaults to my_deck.
    use_belief=False uses the placeholder determinization (control condition).
    margin: Conservative Override. Keep the rule-based first move unless another
            candidate's rollout win rate exceeds it by >= margin. margin=0 with a
            tie-break toward rule-based already guarantees "search never makes the
            agent worse than the rule-based baseline" up to Monte-Carlo noise; a
            small positive margin (e.g. 0.1) suppresses noisy overrides further."""
    opp_deck = opp_deck or my_deck
    rng = random.Random(seed)
    determinize = belief_determinize if use_belief else _placeholder_determinize
    base = B.make_policy_agent("lucario_v2")     # default / candidate source
    pol_me = B.make_policy_agent("lucario_v2")   # rollout: our side
    pol_opp = B.make_policy_agent("lucario_v2")  # rollout: opponent side

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            return list(my_deck)
        select = obs.select
        n = len(select.option)
        # Only search MAIN single-pick decisions; else defer to rule-based.
        if int(select.type) != MAIN or select.maxCount != 1 or n <= 1:
            try:
                return _clamp(base(obs_dict), select)
            except Exception:
                return _clamp([0], select)

        my_index = obs.current.yourIndex
        # rule-based first move = the baseline we must not fall below.
        rb0 = None
        try:
            rb = base(obs_dict)
            if rb and 0 <= rb[0] < n:
                rb0 = rb[0]
        except Exception:
            rb0 = None
        candidates = list(range(min(n, max_candidates)))
        if rb0 is not None and rb0 not in candidates:
            candidates.append(rb0)

        try:
            vals = {}
            for i in candidates:
                tot = 0.0
                for _ in range(k_rollouts):
                    det = determinize(obs, my_deck, opp_deck, rng)
                    root = api.search_begin(obs, **det)
                    ss = api.search_step(root.searchId, [i])
                    tot += _rollout(ss, pol_me, pol_opp, my_index, horizon)
                    api.search_end()
                vals[i] = tot / k_rollouts
        except Exception:
            try:
                api.search_end()
            except Exception:
                pass
            return _clamp(base(obs_dict), select)

        if not vals:
            return _clamp(base(obs_dict), select)
        # Conservative Override: switch off the rule-based move only if another
        # candidate is clearly (>= margin) better. Otherwise keep rule-based.
        best_other = max(vals, key=vals.get)
        if rb0 is None or rb0 not in vals:
            return [best_other]
        if best_other != rb0 and vals[best_other] >= vals[rb0] + margin:
            return [best_other]
        return [rb0]

    agent.__name__ = "agent_pimc"
    return agent
