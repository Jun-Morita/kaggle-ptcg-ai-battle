"""Deck-dispatching non-ex policy (lucario_v2 + a deck-aware patch).

Goal: ONE policy that pilots whichever deck it is given, by detecting the deck
from `my_deck` and routing the deck-specific hooks. Motivation: the #1 ladder
deck (Debauchery: Hop's Trevenant + Hop's Cramorant + Team Rocket tutor engine)
bricks under the stock/v007 policy (0.167 vs ex) because the tutor engine
(Petrel/Hilda/Transceiver/Secret Box) needs deck-aware SEARCH-TARGET selection,
and Cramorant/Postwick are unmodeled. This patch adds, for non-ex Hop's decks:

  1. dispatch `_base_attack` per card (Lucario cards -> original; non-ex -> model)
  2. non-ex attack model incl. **Hop's Cramorant** (1 energy 120 when opp has 3-4
     prizes), **Postwick** (+30 to Hop's attacks, stadium), Extra Helpings (+30
     from benched Hop's Snorlax), Hop's Choice Band (+30 / -1 cost)
  3. correct Weakness type in `_plan_attack` (Psychic for Trevenant/Phantump)
  4. **search-target priority** (`_score_to_hand`) so tutors fetch Phantump -> energy
     -> Trevenant/Cramorant -> Choice Band and the board actually sets up

For Lucario / other decks the original logic is used unchanged (dispatch is gated
on `_DECK_NONEX`). PATCH_SRC is reused by the submission builder.
"""
from __future__ import annotations
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
POLICIES = os.path.join(ROOT, "workspace", "exp002_baselines", "policies")
EXP12 = os.path.join(ROOT, "workspace", "exp012_nonex")

PATCH_SRC = '''
# ===== deck-dispatch: non-ex Hop's attack model + search priority =====
_TREVENANT, _CRAMORANT, _SNORLAX, _PHANTUMP = 879, 311, 304, 878
_DUDUNSPARCE, _DUNSPARCE = 66, 65
_POSTWICK, _CHOICE_BAND = 1255, 1171
_HOPS = {_TREVENANT, _CRAMORANT, _SNORLAX, _PHANTUMP}          # get Postwick / Extra Helpings boosts
_NONEX_ATTACKERS = {_TREVENANT, _CRAMORANT, _SNORLAX, _PHANTUMP, _DUDUNSPARCE, _DUNSPARCE}
_NONEX_ENERGY = (19, 11, 12)  # Telepath Psychic / Mist / Legacy
_DECK_NONEX = (_TREVENANT in my_deck) or (_PHANTUMP in my_deck)

def _hops_boost(self, pokemon):
    b = 0
    if pokemon.id in _HOPS:
        if self.stadium_id == _POSTWICK:
            b += 30
        if any(p is not None and p.id == _SNORLAX for p in self._my_board()):
            b += 30
    return b

def _nonex_base_attack(self, pokemon, attack_index):
    boost = _hops_boost(self, pokemon)
    has_cb = any(getattr(t, "id", None) == _CHOICE_BAND for t in pokemon.tools)
    cb_d = 30 if has_cb else 0
    cb_c = 1 if has_cb else 0
    pid = pokemon.id
    if pid == _TREVENANT:
        if attack_index == 0:   # Horrifying Revenge: 1 energy, 30, Psychic (main attacker)
            return (max(0, 1 - cb_c), 30 + boost + cb_d, 60)
        if attack_index == 1:   # Corner: 3 energy, 90, no-retreat
            return (max(0, 3 - cb_c), 90 + boost + cb_d, 10)
        return None
    if pid == _CRAMORANT:       # Fickle Spitting: 1 energy 120, ONLY if opp has 3-4 prizes
        if attack_index == 0 and len(self.opponent.prize) in (3, 4):
            return (max(0, 1 - cb_c), 120 + boost + cb_d, 80)
        return None
    if pid == _SNORLAX:         # Dynamic Press 140 (80 recoil); prefer benched for Extra Helpings
        if attack_index == 0:
            return (max(0, 3 - cb_c), 140 + boost + cb_d, -160)
        return None
    if pid == _DUDUNSPARCE:     # Land Crush 90 (not Hop's -> no boost); draw engine, low priority
        if attack_index == 0:
            return (max(0, 3 - cb_c), 90 + cb_d, -110)
        return None
    if pid == _DUNSPARCE:
        if attack_index == 0:
            return (max(0, 1 - cb_c), 10 + cb_d, -160)
        return None
    if pid == _PHANTUMP:
        if attack_index == 0:
            return (max(0, 1 - cb_c), 10 + boost + cb_d, -160)
        return None
    return None

_orig_base_attack = LucarioPolicy._base_attack
def _disp_base_attack(self, pokemon, attack_index):
    if _DECK_NONEX and pokemon.id in _NONEX_ATTACKERS:
        return _nonex_base_attack(self, pokemon, attack_index)
    return _orig_base_attack(self, pokemon, attack_index)
LucarioPolicy._base_attack = _disp_base_attack

def _nonex_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    have_e = sum(self.hand_counts[e] for e in _NONEX_ENERGY) >= 1
    for ai, me in enumerate(self._my_board()):
        if me is None:
            continue
        if ai != 0 and not self.can_switch:
            break
        atk_type = EnergyType.PSYCHIC if me.id in (_TREVENANT, _PHANTUMP) else EnergyType.COLORLESS
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
                od = card_table[op.id]
                if atk_type != EnergyType.COLORLESS and od.weakness == atk_type:
                    d *= 2
                elif atk_type != EnergyType.COLORLESS and od.resistance == atk_type:
                    d = max(0, d - 30)
                sc = target_score(op)
                prize = prize_count(op) if op.hp <= d else 0
                if prize == 0:
                    sc *= d / op.hp
                if len(self.opponent.prize) <= prize:
                    sc = 50000
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)

_orig_plan_attack = LucarioPolicy._plan_attack
def _disp_plan_attack(self):
    if _DECK_NONEX:
        return _nonex_plan_attack(self)
    return _orig_plan_attack(self)
LucarioPolicy._plan_attack = _disp_plan_attack

# search-target priority so the tutor engine sets up the board
_TO_HAND_PRI = {878: 320, 879: 300, 311: 270, 19: 240, 11: 220, 1171: 200,
                304: 180, 1182: 175, 1225: 160, 1219: 150, 1134: 145, 1115: 140,
                66: 135, 65: 120}
def _nonex_score_to_hand(self, card):
    pid = card.id
    s = _TO_HAND_PRI.get(pid, 100) - self.hand_counts[pid] * 60
    if pid == 879 and self.field_counts[878] == 0 and self.hand_counts[878] == 0 and self.field_counts[879] == 0:
        s -= 160   # Trevenant useless with no Phantump to evolve
    if pid == 304 and (self.field_counts[304] >= 1 or self.hand_counts[304] >= 1):
        s -= 220   # one benched Snorlax is plenty
    return s

_orig_score_to_hand = LucarioPolicy._score_to_hand
def _disp_score_to_hand(self, card):
    if _DECK_NONEX:
        return _nonex_score_to_hand(self, card)
    return _orig_score_to_hand(self, card)
LucarioPolicy._score_to_hand = _disp_score_to_hand
'''

_n = [0]


def make_agent(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"router_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
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


def debauchery_deck():
    return json.load(open(os.path.join(EXP12, "debauchery_deck.json")))


def charmq_deck():
    return json.load(open(os.path.join(EXP12, "charmq_deck.json")))
