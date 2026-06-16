"""Baseline agents for the PTCG harness.

Each agent is a callable `agent(obs_dict) -> list[int]` following the Kaggle
contract. Keep agents self-contained so they can be copied into a Kaggle
`main.py` with minimal changes.
"""
from __future__ import annotations

import os
import random

from harness import load_engine

_api, _ = load_engine()
to_observation_class = _api.to_observation_class


def read_deck(path: str) -> list[int]:
    with open(path) as f:
        rows = [r for r in f.read().split("\n") if r.strip()]
    return [int(rows[i]) for i in range(60)]


# Default sample deck shipped with the engine.
SAMPLE_DECK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "sim_sample", "deck.csv"
)


def make_random_agent(deck_path: str = SAMPLE_DECK_PATH, seed: int | None = None):
    """An agent that returns a fixed deck then picks valid random selections."""
    deck = read_deck(deck_path)
    rng = random.Random(seed)

    def agent(obs_dict: dict) -> list[int]:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        s = obs.select
        n = len(s.option)
        k = rng.randint(s.minCount, s.maxCount)
        if k <= 0:
            return []
        return rng.sample(range(n), min(k, n))

    return agent
