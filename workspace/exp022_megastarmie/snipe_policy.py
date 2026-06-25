"""Mega Starmie informed pilot — FIX #1: Jetting Blow snipe targeting (gust-style single fix).

Real-strategy rule (official Mega Starmie ex guide): Jetting Blow's +50 bench damage should
snipe the opponent's DEVELOPING BASICS (low HP, ~70) to kill them before they evolve / set up
a future KO ("force them to bench duplicates, one dies before evolving"). The bench target is
chosen in SelectContext.DAMAGE; our generic policy scores it 0 (hits bench slot 0 arbitrarily).
This minimal override picks a KO (prize, prefer ex) else the lowest-HP target. Built on the
GENERIC base (higher floor than our explicit Mega plan, which kept underperforming in exp022).
PATCH_SRC consumed by build_submission.py.
"""
from __future__ import annotations
import importlib.util
import os
import sys

PATCH_SRC = '''
# ===== FIX #1: Jetting Blow bench-snipe targeting (SelectContext.DAMAGE) =====
_orig_score_card_choice = LucarioPolicy._score_card_choice
def _snipe_score_card_choice(self, option):
    # only snipe the OPPONENT's bench (DAMAGE context also fires for self-damage placement)
    if self.context == SelectContext.DAMAGE and option.playerIndex != self.my_index:
        card = get_card(self.obs, option.area, option.index, option.playerIndex)
        if isinstance(card, Pokemon):
            # card.hp is REMAINING hp (KO check elsewhere is hp <= damage)
            if card.hp <= 50:                     # the +50 KOs it -> take a prize; prefer ex (more prizes)
                return 5000 + 1000 * prize_count(card)
            return 2000 - card.hp                 # else soften the lowest-HP target (developing basics ~70)
    return _orig_score_card_choice(self, option)
LucarioPolicy._score_card_choice = _snipe_score_card_choice
'''

_n = [0]


def make_agent(deck):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp013_router"))
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"snipe_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
