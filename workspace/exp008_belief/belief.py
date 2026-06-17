"""Belief-grounded determinization for the Search API (exp008, pillar A).

Instead of filling the opponent with placeholder Snorlax/energy (which makes
search plan against a fake passive opponent — the bottleneck found in
exp003/004/006), we sample the opponent's hidden cards from a *real* believed
decklist, so a rule-based rollout inside the search plays the opponent's actual
strategy.

v1 keeps it simple and robust: sample each hidden pile from the believed
decklist (independent sampling — an approximate but legal "possible world").
The important change vs placeholder is that the cards are real (real Pokémon,
trainers, energy), so the opponent in rollouts behaves realistically.
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
_all = api.all_card_data()
_card = {c.cardId: c for c in _all}


def basic_pokemon_ids(decklist):
    return [cid for cid in decklist if _card.get(cid) and _card[cid].basic]


def _sample(pool, k, rng):
    if k <= 0:
        return []
    if k <= len(pool):
        return rng.sample(pool, k)
    # need more than available: sample with replacement (approx possible world)
    return [rng.choice(pool) for _ in range(k)]


def belief_determinize(obs, my_deck, opp_deck, rng):
    """Return kwargs for api.search_begin grounded in believed decklists.

    my_deck / opp_deck: believed full 60-card decklists (card IDs).
    """
    st = obs.current
    yi = st.yourIndex
    me = st.players[yi]
    opp = st.players[1 - yi]

    # my hidden = deck + prize, sampled from my decklist (I know my hand/board,
    # but a simple legal sampling from the full list is sufficient and robust).
    your_deck = _sample(list(my_deck), me.deckCount, rng)
    your_prize = _sample(list(my_deck), len(me.prize), rng)

    # opponent hidden = deck + hand + prize, sampled from the believed opp deck.
    opponent_deck = _sample(list(opp_deck), opp.deckCount, rng)
    opponent_hand = _sample(list(opp_deck), opp.handCount, rng)
    opponent_prize = _sample(list(opp_deck), len(opp.prize), rng)

    # face-down opponent active (setup) needs a real Basic Pokémon id.
    active = opp.active
    if len(active) > 0 and active[0] is None:
        basics = basic_pokemon_ids(opp_deck)
        opponent_active = [basics[0] if basics else 1072]
    else:
        opponent_active = []

    return dict(
        your_deck=your_deck,
        your_prize=your_prize,
        opponent_deck=opponent_deck,
        opponent_prize=opponent_prize,
        opponent_hand=opponent_hand,
        opponent_active=opponent_active,
    )
