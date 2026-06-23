"""exp020: ORIGINAL anti-mirror deck — Tinkaton "Windup Swing" + pilot patch.

Concept (our own build, not a copy): Tinkaton's Windup Swing does 240 for 1 Metal
energy, MINUS 60 per energy on the opponent's active. So it hits LOW-energy targets
(non-ex single-prize attackers = our weak mirror, and setup mons) for ~180-240, but
high-energy ex for less. A structural counter to the non-ex mirror we lose at 0.40.

Pilot patch (lucario_v2 base, gated on Tinkaton in deck): teaches the Tinkaton line
attacks, applies the conditional damage in the attack plan (per target energy),
Metal-type weakness, Choice Band, and a search-target priority for the engine
(Tinkatink -> Rare Candy -> Tinkaton -> Metal energy). S2 line set up via Rare Candy.
"""
from __future__ import annotations
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
POLICIES = os.path.join(ROOT, "workspace", "exp002_baselines", "policies")

PATCH_SRC = '''
# ===== Tinkaton anti-mirror attack model + search priority =====
_TINKATINK, _TINKATUFF, _TINKATON = 697, 698, 699
_METAL_E, _CHOICE_BAND = 8, 1171
_RARE_CANDY, _BOSS = 1079, 1182
_TINKA_LINE = {_TINKATINK, _TINKATUFF, _TINKATON}
_DECK_TINKA = _TINKATON in my_deck

def _tinka_base_attack(self, pokemon, ai):
    has_cb = any(getattr(t, "id", None) == _CHOICE_BAND for t in pokemon.tools)
    cb_d = 30 if has_cb else 0
    cb_c = 1 if has_cb else 0
    pid = pokemon.id
    if pid == _TINKATON and ai == 0:      # Windup Swing: 240 base (conditional in plan), 1 Metal
        return (max(0, 1 - cb_c), 240 + cb_d, 80)
    if pid == _TINKATUFF and ai == 0:     # Light Punch 30 (bridge attacker)
        return (max(0, 1 - cb_c), 30 + cb_d, -100)
    if pid == _TINKATINK and ai == 0:     # Beat 20 (last resort)
        return (max(0, 1 - cb_c), 20 + cb_d, -160)
    return None

_orig_base_attack = LucarioPolicy._base_attack
def _disp_base_attack(self, pokemon, attack_index):
    if _DECK_TINKA and pokemon.id in _TINKA_LINE:
        return _tinka_base_attack(self, pokemon, attack_index)
    return _orig_base_attack(self, pokemon, attack_index)
LucarioPolicy._base_attack = _disp_base_attack

def _tinka_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    have_e = self.hand_counts[_METAL_E] >= 1
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
                if have_e and not self.state.energyAttached:
                    ecount += 1
                    needs_e = ecount >= need
                if not needs_e:
                    continue
            for ti, op in enumerate(self._opponent_board()):
                if op is None:
                    continue
                if ti != 0 and not self.can_gust:
                    break
                d = dmg
                if me.id == _TINKATON and idx == 0:        # Windup Swing conditional
                    d = max(0, d - 60 * len(op.energies))
                od = card_table[op.id]
                if od.weakness == EnergyType.METAL:
                    d *= 2
                elif od.resistance == EnergyType.METAL:
                    d = max(0, d - 30)
                sc = target_score(op)
                prize = prize_count(op) if op.hp <= d else 0
                if prize == 0:
                    sc *= d / op.hp if op.hp else 0
                if len(self.opponent.prize) <= prize:
                    sc = 50000
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)

_orig_plan_attack = LucarioPolicy._plan_attack
def _disp_plan_attack(self):
    if _DECK_TINKA:
        return _tinka_plan_attack(self)
    return _orig_plan_attack(self)
LucarioPolicy._plan_attack = _disp_plan_attack

# search-target priority so the engine sets up the Tinkaton line
_TINKA_PRI = {_TINKATINK: 320, _RARE_CANDY: 300, _TINKATON: 280, _METAL_E: 240,
              _TINKATUFF: 200, _CHOICE_BAND: 170, _BOSS: 150}
def _tinka_score_to_hand(self, card):
    pid = card.id
    s = _TINKA_PRI.get(pid, 100) - self.hand_counts[pid] * 60
    if pid == _TINKATON and self.field_counts[_TINKATINK] == 0 and self.hand_counts[_TINKATINK] == 0 \
            and self.field_counts[_TINKATUFF] == 0 and self.field_counts[_TINKATON] == 0:
        s -= 160                       # Tinkaton useless with no line to evolve
    if pid == _RARE_CANDY and self.field_counts[_TINKATINK] == 0 and self.hand_counts[_TINKATINK] == 0:
        s -= 120                       # Rare Candy needs a Tinkatink target
    if pid == _METAL_E and self.state.energyAttached:
        s -= 80
    return s

_orig_score_to_hand = LucarioPolicy._score_to_hand
def _disp_score_to_hand(self, card):
    if _DECK_TINKA:
        return _tinka_score_to_hand(self, card)
    return _orig_score_to_hand(self, card)
LucarioPolicy._score_to_hand = _disp_score_to_hand
'''

_n = [0]


def make_agent(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"tinka_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
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


def tinkaton_deck():
    return json.load(open(os.path.join(HERE, "tinkaton_deck.json")))
