"""Mega Starmie ex + Mega Froslass ex pilot patch (exp022) — research the piloting knack.

Feasibility (SESSION_NOTES): the GENERIC policy already pilots this deck to 0.825 vs our
non-ex but only 0.10 vs Crustle / 0.475 vs ex, because it has no attack model for the
Mega-ex line and never uses Mega Starmie's Nebula Beam (210, "isn't affected by ... any
effects on opponent's Active Pokémon") which is the ONLY way to pierce Crustle's
ex-damage-negating Safeguard. This patch teaches the deck, mirroring exp013's structure:
  - `_base_attack` model for Mega Starmie / Mega Froslass.
  - `_plan_attack`: Water-type weakness; Nebula Beam ignores weakness AND pierces walls;
    every other (ex) attack deals 0 into a Crustle/Dwebble wall -> forces Nebula Beam there.
  - search-target priority to set up the Staryu/Snorunt -> Mega line + Water energy.
PATCH_SRC is consumed by scripts/build_submission.py.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp001_harness"),
           os.path.join(_ROOT, "workspace", "exp013_router")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import router_policy as R  # for POLICIES path + make_agent pattern

PATCH_SRC = '''
# ===== Mega Starmie ex + Mega Froslass ex attack model =====
_MSTARMIE, _MFROSLASS = 1031, 861
_STARYU, _SNORUNT = 1030, 860
_MEGA_ATTACKERS = {_MSTARMIE, _MFROSLASS}
_DECK_MEGA = (_MSTARMIE in my_deck) or (_MFROSLASS in my_deck)
_CRUSTLE, _DWEBBLE = 345, 344
_NEBULA = 1  # Mega Starmie attack_index 1 (Nebula Beam) — pierces walls, ignores weakness

def _mega_is_wall(self):
    return any(p is not None and p.id in (_CRUSTLE, _DWEBBLE) for p in self._opponent_board())

def _mega_base_attack(self, pokemon, attack_index):
    # returns (energy_needed, damage, base_score); damage before weakness
    pid = pokemon.id
    if pid == _MSTARMIE:
        if attack_index == 0:        # Jetting Blow: 1 W, 120 (+50 bench) — THE WORKHORSE (tomatomato uses it every turn)
            return (1, 120, 160)
        if attack_index == 1:        # Nebula Beam: 3, 210, ignores weakness/resist + opp-active effects (finisher only)
            return (3, 210, 60)
        return None
    if pid == _MFROSLASS:
        if attack_index == 0:        # Resentful Refrain: 1 W, 50 x opp hand size
            return (1, 50 * max(1, len(self.opponent.hand)), 40)
        if attack_index == 1:        # Absolute Snow: 3 (W + 2), 150 + opponent Asleep
            return (3, 150, 70)
        return None
    return None

_orig_base_attack = LucarioPolicy._base_attack
def _disp_base_attack(self, pokemon, attack_index):
    if _DECK_MEGA and pokemon.id in _MEGA_ATTACKERS:
        return _mega_base_attack(self, pokemon, attack_index)
    return _orig_base_attack(self, pokemon, attack_index)
LucarioPolicy._base_attack = _disp_base_attack

def _mega_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    have_e = self.hand_counts[3] >= 1 and not self.state.energyAttached  # Basic Water in hand
    wall = _mega_is_wall(self)
    for ai, me in enumerate(self._my_board()):
        if me is None:
            continue
        if ai != 0 and not self.can_switch:
            break
        for idx in range(2):
            at = self._base_attack_after_evolution(me, ai, idx)
            if at is None:
                continue
            need, dmg, bscore = at
            ecount = len(me.energies)
            needs_e = False
            if ecount < need:
                if have_e:
                    ecount += 1
                    needs_e = ecount >= need
                if not needs_e:
                    continue
            is_nebula = (me.id == _MSTARMIE and idx == _NEBULA)  # pierces walls, ignores weakness
            for ti, op in enumerate(self._opponent_board()):
                if op is None:
                    continue
                if ti != 0 and not self.can_gust:
                    break
                d = dmg
                od = card_table[op.id]
                if not is_nebula:
                    if od.weakness == EnergyType.WATER:
                        d *= 2
                    elif od.resistance == EnergyType.WATER:
                        d = max(0, d - 30)
                # NOTE: tomatomato beats Crustle with Jetting Blow (the 120+50 spread connects),
                # so we do NOT zero out damage vs walls — that suppressed our real win condition.
                sc = target_score(op)
                prize = prize_count(op) if op.hp <= d else 0
                if prize == 0:
                    sc *= d / op.hp if op.hp else 0
                if len(self.opponent.prize) <= prize:
                    sc = 50000
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                if me.id == _MSTARMIE and idx == 0:
                    sc += 40  # Jetting Blow's +50 bench spread is real extra value
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)

_orig_plan_attack = LucarioPolicy._plan_attack
def _disp_plan_attack(self):
    if _DECK_MEGA:
        return _mega_plan_attack(self)
    return _orig_plan_attack(self)
LucarioPolicy._plan_attack = _disp_plan_attack

# search/draw priority: set up the Staryu/Snorunt -> Mega line + Water energy
_MEGA_TO_HAND_PRI = {_STARYU: 320, _SNORUNT: 300, _MSTARMIE: 290, _MFROSLASS: 270,
                     3: 240, 1145: 200, 1182: 175, 1229: 150, 1119: 140}
def _mega_score_to_hand(self, card):
    pid = card.id
    s = _MEGA_TO_HAND_PRI.get(pid, 100) - self.hand_counts[pid] * 50
    if pid == _MSTARMIE and self.field_counts[_STARYU] == 0 and self.hand_counts[_STARYU] == 0:
        s -= 160   # Mega Starmie needs a Staryu to evolve from
    if pid == _MFROSLASS and self.field_counts[_SNORUNT] == 0 and self.hand_counts[_SNORUNT] == 0:
        s -= 160
    return s

_orig_score_to_hand = LucarioPolicy._score_to_hand
def _disp_score_to_hand(self, card):
    if _DECK_MEGA:
        return _mega_score_to_hand(self, card)
    return _orig_score_to_hand(self, card)
LucarioPolicy._score_to_hand = _disp_score_to_hand

# ===== sequencing: CONCENTRATE energy onto ONE Mega Starmie -> reach 3-energy Nebula Beam =====
# The deck's power is one big Nebula Beam (210, pierces Crustle Safeguard). Spreading energy
# across Megas never reaches it. Favor the Mega Starmie closest to 3 energy (finish it), and
# vs a wall push HARD toward Nebula Beam since it's the only attack that connects.
def _mega_energy_target_score(self, pokemon, active):
    pid = pokemon.id
    if pid not in (_MSTARMIE, _MFROSLASS, _STARYU, _SNORUNT):
        return _orig_ets(self, pokemon, active)
    ec = len(pokemon.energies)
    score = 8000 + (10 if active else 0)
    wall = _mega_is_wall(self)
    if pid == _MSTARMIE:
        if ec < 3:
            score += 200 + ec * 80         # the closer to 3, the more we want to finish THIS one
            if wall:
                score += 150               # vs wall, Nebula Beam is the only out -> rush it
        else:
            score -= 300                   # already armed for Nebula Beam; don't overload
        if active:
            score += 40
    elif pid == _MFROSLASS:
        if wall:
            score -= 200                   # Froslass (ex) can't connect through Safeguard
        elif ec < 1:
            score += 120                   # 1 energy = Resentful Refrain online
        elif ec < 3:
            score += 50
        else:
            score -= 120
    else:                                  # un-evolved Staryu/Snorunt: evolve first, energy later
        score -= 60
    return score

_orig_ets = LucarioPolicy._energy_target_score
def _disp_energy_target_score(self, pokemon, active):
    if _DECK_MEGA:
        return _mega_energy_target_score(self, pokemon, active)
    return _orig_ets(self, pokemon, active)
LucarioPolicy._energy_target_score = _disp_energy_target_score
'''

_n = [0]


def make_agent(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"starmie_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
