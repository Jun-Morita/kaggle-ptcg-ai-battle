"""Load the extracted rule-based policies as harness-compatible agents.

Reuses exp001's harness (engine loading, run_match/run_gauntlet). Each policy
module exposes `agent(obs_dict)`; we wrap it so the deck is injected on the
initial (select is None) call instead of relying on its deck.csv reading.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
if EXP1 not in sys.path:
    sys.path.insert(0, EXP1)

from harness import load_engine  # noqa: E402

_api, _ = load_engine()  # must load cg before importing policy modules
to_observation_class = _api.to_observation_class

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")

with open(os.path.join(POLICIES_DIR, "decks.json")) as f:
    DECKS: dict[str, list[int]] = json.load(f)

POLICY_NAMES = list(DECKS.keys())  # dragapult, iono, abomasnow, lucario_v1, lucario_v2


def _load_module(name: str):
    """Load a policy module. Some policies read deck.csv at import time, so we
    chdir into policies/ with the right deck.csv present, then restore cwd."""
    path = os.path.join(POLICIES_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"policy_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES_DIR)
        with open("deck.csv", "w") as f:
            f.write("\n".join(str(c) for c in DECKS[name]) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def make_policy_agent(name: str):
    """Wrap an extracted policy module into agent(obs_dict)->list[int]."""
    mod = _load_module(name)
    deck = list(DECKS[name])

    def agent(obs_dict: dict) -> list[int]:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        return mod.agent(obs_dict)

    agent.__name__ = f"agent_{name}"
    return agent


def make_random_agent_with_deck(deck: list[int], seed: int | None = None):
    """A random-selection agent that uses the given deck (for fair self-deck tests)."""
    rng = random.Random(seed)

    def agent(obs_dict: dict) -> list[int]:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        s = obs.select
        k = rng.randint(s.minCount, s.maxCount)
        if k <= 0:
            return []
        return rng.sample(range(len(s.option)), min(k, len(s.option)))

    agent.__name__ = "agent_random"
    return agent
