"""exp007: reproduce the Crustle anti-ex control matchup locally and test fixes.

Ground truth (replays): our all-ex Mega Lucario loses ~100% to pure Crustle
control (Dwebble+Crustle, 0 ex) because ex attacks can't damage Crustle's
Safeguard ability. Key: Hariyama (non-ex) Wild Press = 210 dmg one-shots the
150-HP Crustle and bypasses Safeguard.

This module sets up a Crustle opponent in the harness (the real meta decklist,
played by the generic lucario_v2 policy) so we can measure anti-Crustle fixes.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(__file__)
EXP1 = os.path.abspath(os.path.join(HERE, "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(HERE, "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
_api, _ = load_engine()
to_observation_class = _api.to_observation_class

POLICIES = os.path.join(EXP2, "policies")
CRUSTLE_DECK = json.load(open(os.path.join(HERE, "crustle_deck.json")))
with open(os.path.join(POLICIES, "decks.json")) as f:
    LUCARIO_DECK = json.load(f)["lucario_v2"]

_n = [0]


def _load_policy_module(deck):
    """Load a fresh lucario_v2 policy module with `deck` written as deck.csv."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pol_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def make_agent(deck):
    """lucario_v2 generic policy playing an arbitrary deck."""
    mod = _load_policy_module(deck)

    def agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        return mod.agent(obs_dict)
    return agent


def make_crustle_agent():
    return make_agent(CRUSTLE_DECK)


def make_lucario_agent():
    return make_agent(LUCARIO_DECK)


if __name__ == "__main__":
    from harness import run_gauntlet
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ours = make_lucario_agent()
    crustle = make_crustle_agent()
    st = run_gauntlet(ours, crustle, n_games=n, swap_sides=True)
    print(f"Lucario(ours) vs Crustle control: winrate={st.winrate0:.3f} "
          f"({st.wins0}-{st.wins1}-{st.draws}) errors=({st.errors0}+{st.errors1}) "
          f"avg_moves={st.total_moves/st.n:.0f} reasons={st.reasons}")
    print("(ladder ground truth: ~0% — we should reproduce a low win rate)")
