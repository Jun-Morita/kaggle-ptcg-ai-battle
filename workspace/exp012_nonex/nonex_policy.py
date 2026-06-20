"""Dedicated NON-EX (Hop's Trevenant) policy = lucario_v2 + a non-ex attack model.

Diagnosis (exp012): the generic lucario_v2 policy pilots the non-ex deck "blind" —
its `_base_attack` only knows Lucario cards, so for the non-ex deck `_plan_attack`
forms NO plan (attacker=-1, target=0). That silently disables, for the whole game:
  * Boss's Orders   (gated on plan.target>=1)  -> the gust card sits dead
  * retreat/switch  (gated on plan.attacker>=1)
  * attack-target selection + directing energy to the intended attacker
  * any KO/lethal recognition (no damage knowledge)

Fix (v003-style targeted patch, NOT a rewrite): teach `_base_attack` the non-ex
attacks with Extra Helpings (+30 when Hop's Snorlax is in play) and Hop's Choice
Band (+30 dmg / -1 cost), and override `_plan_attack` to use the correct attack
type for Weakness (Psychic for Trevenant/Phantump, else Colorless). Everything
downstream (Boss's Orders, retreat, targeting, energy) is already wired to `plan`
and starts working once a real plan exists.

`make_smart_agent()` returns the patched agent; `make_generic_agent()` the stock
one — for head-to-head mirror testing. The patch text (PATCH_SRC) is reused by the
submission build so the .tar.gz is self-contained.
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
POLICIES = os.path.join(ROOT, "workspace", "exp002_baselines", "policies")
NONEX = json.load(open(os.path.join(HERE, "charmq_deck.json")))

# Appended after lucario_v2's class definition: redefine the two methods and rebind.
PATCH_SRC = '''
# ===== non-ex (Hop's Trevenant) attack model, overriding the Lucario one =====
_HOPS_SNORLAX = 304
_HOPS_TREVENANT = 879
_HOPS_PHANTUMP = 878
_DUDUNSPARCE = 66
_DUNSPARCE = 65
_HOPS_CHOICE_BAND = 1171
_NONEX_ENERGY_IDS = (11, 19, 12)  # Mist / Telepath Psychic / Legacy

def _nonex_base_attack(self, pokemon, attack_index):
    extra = 30 if any(p is not None and p.id == _HOPS_SNORLAX for p in self._my_board()) else 0
    has_cb = any(getattr(t, "id", None) == _HOPS_CHOICE_BAND for t in pokemon.tools)
    cb_dmg = 30 if has_cb else 0
    cb_cost = 1 if has_cb else 0
    pid = pokemon.id
    if pid == _HOPS_TREVENANT:
        if attack_index == 0:   # Horrifying Revenge: 1 energy, 30 base, Psychic (main attacker)
            return (max(0, 1 - cb_cost), 30 + extra + cb_dmg, 60)
        if attack_index == 1:   # Corner: 3 energy, 90, locks retreat
            return (max(0, 3 - cb_cost), 90 + extra + cb_dmg, 10)
        return None
    if pid == _HOPS_SNORLAX:    # prefer benched for Extra Helpings; attack only when it KOs
        if attack_index == 0:   # Dynamic Press 140 (80 recoil)
            return (max(0, 3 - cb_cost), 140 + extra + cb_dmg, -160)
        return None
    if pid == _DUDUNSPARCE:     # draw engine; low attack priority
        if attack_index == 0:   # Land Crush 90 (colorless, no Extra Helpings)
            return (max(0, 3 - cb_cost), 90 + cb_dmg, -110)
        return None
    if pid == _DUNSPARCE:
        if attack_index == 0:   # Gnaw 10
            return (max(0, 1 - cb_cost), 10 + cb_dmg, -160)
        return None
    if pid == _HOPS_PHANTUMP:
        if attack_index == 0:   # Splashing Dodge 10
            return (max(0, 1 - cb_cost), 10 + extra + cb_dmg, -160)
        return None
    return None

def _nonex_plan_attack(self):
    global plan
    best_score = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    have_energy = sum(self.hand_counts[e] for e in _NONEX_ENERGY_IDS) >= 1
    for attacker_index, my_pokemon in enumerate(self._my_board()):
        if my_pokemon is None:
            continue
        if attacker_index != 0 and not self.can_switch:
            break
        atk_type = EnergyType.PSYCHIC if my_pokemon.id in (_HOPS_TREVENANT, _HOPS_PHANTUMP) else EnergyType.COLORLESS
        for attack_index in range(2):
            attack = self._base_attack_after_evolution(my_pokemon, attacker_index, attack_index)
            if attack is None:
                continue
            energy_required, base_damage, base_score = attack
            energy_count = len(my_pokemon.energies)
            needs_energy = False
            if energy_count < energy_required:
                if have_energy and not self.state.energyAttached:
                    energy_count += 1
                    needs_energy = energy_count >= energy_required
                if not needs_energy:
                    continue
            for target_index, op_pokemon in enumerate(self._opponent_board()):
                if op_pokemon is None:
                    continue
                if target_index != 0 and not self.can_gust:
                    break
                damage = base_damage
                op_data = card_table[op_pokemon.id]
                if atk_type != EnergyType.COLORLESS and op_data.weakness == atk_type:
                    damage *= 2
                elif atk_type != EnergyType.COLORLESS and op_data.resistance == atk_type:
                    damage = max(0, damage - 30)
                score = target_score(op_pokemon)
                prize = prize_count(op_pokemon) if op_pokemon.hp <= damage else 0
                if prize == 0:
                    score *= damage / op_pokemon.hp
                if len(self.opponent.prize) <= prize:
                    score = 50000
                score += base_score
                score += 220 if attacker_index == 0 else 0
                score += 300 if target_index == 0 else 0
                score += energy_count
                if score > best_score:
                    best_score = score
                    plan = AttackPlan(attacker=attacker_index, target=target_index,
                                      attack_index=attack_index,
                                      remain_hp=op_pokemon.hp - damage, needs_energy=needs_energy)

LucarioPolicy._base_attack = _nonex_base_attack
LucarioPolicy._plan_attack = _nonex_plan_attack
'''

_n = [0]


def _load(deck, patched):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"nonex_{patched}_{_n[0]}",
                                                  os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if patched:
        exec(PATCH_SRC, mod.__dict__)
    return mod


def make_smart_agent():
    mod = _load(NONEX, True)
    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(NONEX) if o.select is None else mod.agent(obs_dict)
    return agent


def make_generic_agent():
    mod = _load(NONEX, False)
    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(NONEX) if o.select is None else mod.agent(obs_dict)
    return agent
