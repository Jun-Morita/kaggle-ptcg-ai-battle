"""exp048 -- hand-tuned patch making the generic lucario_v2 pilot for the
Mega Starmie ex / Mega Froslass ex deck (tomatomato/taksai, LB top players)
closer to their observed real play. NOT for shipping -- this exists purely to
build a stronger LOCAL OPPONENT for testing whether v016-wall really loses to
this archetype at good piloting (see exp011/scout-top findings: taksai and
tomatomato beat crustle_control-labeled opponents 22-2 combined, but our own
local test with the UNPATCHED generic pilot showed v016-wall winning 57-3 --
a large, suspicious swing consistent with generic mis-piloting, exp022's
"deck x pilot" lesson).

Findings from policy_diff_fixed.py (fixed next-step pairing, 537 real games):
  - SETUP_ACTIVE_POKEMON/TO_ACTIVE/SWITCH/TO_BENCH (~500 combined decisions,
    match rate 0.35-0.83): tomatomato consistently picks Staryu (-> Mega
    Starmie ex, the deck's primary attacker) as active/lead, where the
    unpatched generic policy picks Snorunt (-> Mega Froslass ex, support/
    tech piece) -- pure tie-break with zero card-specific bonus in the base
    policy (Staryu/Snorunt aren't in lucario_v2's card table C at all).
  - TO_HAND: generic policy over-fetches Ignition Energy (50 vs their 1 --
    wrong energy type for this pure-Water deck, likely dead-card fetching)
    and under-fetches Legacy Energy (35 vs their 159).

These are the highest-volume, cleanest divergences; encode them as bonuses on
top of the untouched generic scoring (same wrapping pattern as anti_crustle.py
-- fresh module instance per call, no cross-agent contamination).
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
EXP1 = os.path.join(ROOT, "workspace", "exp001_harness")
EXP2 = os.path.join(ROOT, "workspace", "exp002_baselines")
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
_api, _ = load_engine()
to_observation_class = _api.to_observation_class

POLICIES = os.path.join(EXP2, "policies")

STARYU = 1030
MEGA_STARMIE_EX = 1031
SNORUNT = 860
MEGA_FROSLASS_EX = 861
LEGACY_ENERGY = 12
IGNITION_ENERGY = 17

_n = [0]


def _load_patched_module(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"msm_pol_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    Policy = mod.LucarioPolicy
    _orig_setup = Policy._score_setup_active
    _orig_to_hand = Policy._score_to_hand
    _orig_card_choice = Policy._score_card_choice

    # NOTE: deliberately NOT touching _score_active_choice (SWITCH/TO_ACTIVE) --
    # a flat Staryu bonus there made unevolved Staryu beat an already-evolved
    # Mega Starmie ex candidate (a worse error than the one being fixed).
    # SETUP_ACTIVE_POKEMON and TO_BENCH candidates are only ever basics (deck/
    # hand at the start of the game), so a flat bonus is safe there.

    def _score_setup_active(self, card):
        score = _orig_setup(self, card)
        if card.id == STARYU:
            score += 5
        return score

    def _score_to_hand(self, card):
        score = _orig_to_hand(self, card)
        if card.id == LEGACY_ENERGY:
            score += 150
        elif card.id == IGNITION_ENERGY:
            score -= 190
        return score

    def _score_card_choice(self, option):
        score = _orig_card_choice(self, option)
        if self.context == mod.SelectContext.TO_BENCH:
            card = mod.get_card(self.obs, option.area, option.index, option.playerIndex)
            cid = getattr(card, "id", None)
            if cid == STARYU:
                score += 30
            elif cid == MEGA_STARMIE_EX:
                score += 20
        return score

    Policy._score_setup_active = _score_setup_active
    Policy._score_to_hand = _score_to_hand
    Policy._score_card_choice = _score_card_choice
    return mod


def make_agent(deck):
    mod = _load_patched_module(deck)

    def agent(obs_dict):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        return mod.agent(obs_dict)
    return agent


if __name__ == "__main__":
    deck = json.load(open(os.path.join(HERE, "..", "exp011_meta_watch", "tomatomato_deck.json")))
    a = make_agent(deck)
    print("loaded OK,", len(deck), "cards")
