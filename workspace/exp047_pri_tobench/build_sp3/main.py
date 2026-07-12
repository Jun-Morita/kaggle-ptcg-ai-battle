from __future__ import annotations

import os
from collections import defaultdict

from cg.api import (
    AreaType,
    Card,
    CardType,
    EnergyType,
    Observation,
    OptionType,
    Pokemon,
    SelectContext,
    all_card_data,
    to_observation_class,
)


class C:
    MAKUHITA = 673
    HARIYAMA = 674
    LUNATONE = 675
    SOLROCK = 676
    RIOLU = 677
    MEGA_LUCARIO_EX = 678

    BASIC_FIGHTING_ENERGY = 6
    DUSK_BALL = 1102
    SWITCH = 1123
    PREMIUM_POWER_PRO = 1141
    FIGHTING_GONG = 1142
    POKE_PAD = 1152
    HERO_CAPE = 1159
    BOSS_ORDERS = 1182
    CARMINE = 1192
    LILLIE_DETERMINATION = 1227
    GRAVITY_MOUNTAIN = 1252

    LUMIOSE_CITY = 1267
    LILLIES_PEARL = 1172
    LEGACY_ENERGY = 12


MEGA_BRAVE = 983
LOW_DECK_COUNT = 8


DECK_PATH = "deck.csv"
if not os.path.exists(DECK_PATH):
    DECK_PATH = "/kaggle_simulations/agent/deck.csv"
with open(DECK_PATH, "r", encoding="utf-8") as f:
    my_deck = [int(line) for line in f.read().splitlines() if line.strip()]


all_card = all_card_data()
card_table = {card.cardId: card for card in all_card}


class AttackPlan:
    def __init__(
        self,
        attacker: int = -1,
        target: int = -1,
        attack_index: int = -1,
        remain_hp: int = -1,
        needs_energy: bool = False,
    ):
        self.attacker = attacker
        self.target = target
        self.attack_index = attack_index
        self.remain_hp = remain_hp
        self.needs_energy = needs_energy


plan = AttackPlan()
pre_turn = -1
ability_used = False


def get_card(obs: Observation, area: AreaType, index: int, player_index: int) -> Pokemon | Card | None:
    player = obs.current.players[player_index]
    match area:
        case AreaType.DECK:
            return obs.select.deck[index]
        case AreaType.HAND:
            return player.hand[index]
        case AreaType.DISCARD:
            return player.discard[index]
        case AreaType.ACTIVE:
            return player.active[index]
        case AreaType.BENCH:
            return player.bench[index]
        case AreaType.PRIZE:
            return player.prize[index]
        case AreaType.STADIUM:
            return obs.current.stadium[index]
        case AreaType.LOOKING:
            return obs.current.looking[index]
        case _:
            return None


def prize_count(pokemon: Pokemon) -> int:
    data = card_table[pokemon.id]
    count = 3 if data.megaEx else 2 if data.ex else 1
    for card in pokemon.energyCards:
        if card.id == C.LEGACY_ENERGY:
            count -= 1
    for card in pokemon.tools:
        if card.id == C.LILLIES_PEARL and "Lillie" in data.name:
            count -= 1
    return max(0, count)


def target_score(pokemon: Pokemon) -> int:
    data = card_table[pokemon.id]
    score = prize_count(pokemon) * 1000
    score += len(pokemon.energies) * 150
    score += len(pokemon.tools) * 100
    if data.stage2:
        score += 250
    elif data.stage1:
        score += 130

    if pokemon.id in {144, 322, 323, 337}:  # low-value support Pokemon
        score -= 200
    if pokemon.id == 112 and len(pokemon.energies) >= 1:  # Munkidori
        score += 300
    score += pokemon.hp
    return score


class LucarioPolicy:
    def __init__(self, obs: Observation):
        self.obs = obs
        self.state = obs.current
        self.select = obs.select
        self.context = self.select.context
        self.my_index = self.state.yourIndex
        self.op_index = 1 - self.my_index
        self.me = self.state.players[self.my_index]
        self.opponent = self.state.players[self.op_index]
        self.my_prizes_left = len(self.me.prize)

        self.field_counts = defaultdict(int)
        self.hand_counts = defaultdict(int)
        self.discard_counts = defaultdict(int)
        self.has_ready_lucario_line = False
        self.has_ready_hariyama_line = False
        self.can_switch = False
        self.can_gust = False
        self.can_attack = False
        self.can_use_mega_brave = False
        self.stadium_id = self.state.stadium[0].id if self.state.stadium else 0

        self._count_cards()
        self._scan_main_options()

    def choose(self) -> list[int]:
        if not self.select.option or self.select.maxCount == 0:
            return []

        if self.context == SelectContext.MAIN:
            self._plan_attack()

        scores = [self._score_option(option) for option in self.select.option]
        ranked = [i for i, _ in sorted(enumerate(scores), key=lambda item: item[1], reverse=True)]
        self._remember_lunatone_ability(ranked)
        return ranked[: self.select.maxCount]

    def _count_cards(self) -> None:
        for pokemon in self.me.active + self.me.bench:
            if pokemon is None:
                continue
            self.field_counts[pokemon.id] += 1
            if pokemon.id in {C.MAKUHITA, C.HARIYAMA} and len(pokemon.energies) >= 3:
                self.has_ready_hariyama_line = True
            if pokemon.id in {C.RIOLU, C.MEGA_LUCARIO_EX} and len(pokemon.energies) >= 2:
                self.has_ready_lucario_line = True

        for card in self.me.hand:
            self.hand_counts[card.id] += 1
        for card in self.me.discard:
            self.discard_counts[card.id] += 1

    def _scan_main_options(self) -> None:
        if self.context != SelectContext.MAIN:
            return
        for option in self.select.option:
            if option.type == OptionType.PLAY:
                card = get_card(self.obs, AreaType.HAND, option.index, self.my_index)
                if card.id == C.SWITCH:
                    self.can_switch = True
                elif card.id == C.BOSS_ORDERS:
                    self.can_gust = True
            elif option.type == OptionType.EVOLVE:
                card = get_card(self.obs, AreaType.HAND, option.index, self.my_index)
                if card.id == C.HARIYAMA:
                    self.can_gust = True
            elif option.type == OptionType.RETREAT:
                self.can_switch = True
            elif option.type == OptionType.ATTACK:
                self.can_attack = True
                if option.attackId == MEGA_BRAVE:
                    self.can_use_mega_brave = True

    def _my_board(self) -> list[Pokemon | None]:
        return self.me.active + self.me.bench

    def _opponent_board(self) -> list[Pokemon | None]:
        return self.opponent.active + self.opponent.bench

    def _can_evolve_board_index(self, board_index: int) -> bool:
        for option in self.select.option:
            if option.type != OptionType.EVOLVE:
                continue
            target_index = option.inPlayIndex
            if option.inPlayArea == AreaType.BENCH:
                target_index += 1
            if target_index == board_index:
                return True
        return False

    def _base_attack(self, pokemon: Pokemon, attack_index: int) -> tuple[int, int, int] | None:
        energy_required = 0
        base_damage = 0
        base_score = 0

        if pokemon.id == C.MEGA_LUCARIO_EX:
            if attack_index == 0:
                energy_required = 1
                base_damage = 130
                base_score += 60 * min(3, self.discard_counts[C.BASIC_FIGHTING_ENERGY])
            else:
                energy_required = 2
                base_damage = 270
            if self.my_prizes_left in {2, 3}:
                base_score -= 500
        elif attack_index == 1:
            return None
        elif pokemon.id == C.HARIYAMA:
            energy_required = 3
            base_damage = 210
        elif pokemon.id == C.MAKUHITA:
            return None
        elif pokemon.id == C.SOLROCK and self.field_counts[C.LUNATONE] >= 1:
            energy_required = 1
            base_damage = 70

        if base_damage <= 0:
            return None
        return energy_required, base_damage, base_score

    def _base_attack_after_evolution(self, pokemon: Pokemon, board_index: int, attack_index: int):
        if pokemon.id == C.MAKUHITA and attack_index == 0 and self._can_evolve_board_index(board_index):
            return 3, 210, -100
        return self._base_attack(pokemon, attack_index)

    def _plan_attack(self) -> None:
        global plan
        best_score = -1
        plan = AttackPlan()

        if self.state.turn < 2:
            return

        for attacker_index, my_pokemon in enumerate(self._my_board()):
            if my_pokemon is None:
                continue
            if attacker_index != 0 and not self.can_switch:
                break

            for attack_index in range(2):
                attack = self._base_attack_after_evolution(my_pokemon, attacker_index, attack_index)
                if attack is None:
                    continue
                energy_required, base_damage, base_score = attack

                energy_count = len(my_pokemon.energies)
                if attack_index == 1 and attacker_index == 0 and energy_count >= 2 and not self.can_use_mega_brave:
                    break

                needs_energy = False
                if energy_count < energy_required:
                    if self.hand_counts[C.BASIC_FIGHTING_ENERGY] >= 1 and not self.state.energyAttached:
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
                    if op_data.weakness == EnergyType.FIGHTING:
                        damage *= 2
                    elif op_data.resistance == EnergyType.FIGHTING:
                        damage -= 30

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
                        plan = AttackPlan(
                            attacker=attacker_index,
                            target=target_index,
                            attack_index=attack_index,
                            remain_hp=op_pokemon.hp - damage,
                            needs_energy=needs_energy,
                        )

    def _energy_target_score(self, pokemon: Pokemon, active: bool) -> int:
        energy_count = len(pokemon.energies)
        score = 8000 + (10 if active else 0)

        if pokemon.id in {C.MAKUHITA, C.HARIYAMA}:
            score += 1 if pokemon.id == C.HARIYAMA else 0
            score += 100 if energy_count < 3 else 0
            score -= 50 if self.has_ready_hariyama_line else 0
        elif pokemon.id == C.LUNATONE:
            score -= 100
        elif pokemon.id == C.SOLROCK:
            score += 20 if energy_count < 1 else -100
        elif pokemon.id in {C.RIOLU, C.MEGA_LUCARIO_EX}:
            score += 1 if pokemon.id == C.MEGA_LUCARIO_EX else 0
            score += 100 if energy_count < 2 else 0
            score -= 50 if self.has_ready_lucario_line else 0
        return score

    def _score_option(self, option) -> float:
        if option.type == OptionType.NUMBER:
            return option.number
        if option.type == OptionType.YES:
            return 100 if self.context == SelectContext.IS_FIRST else 1
        if option.type == OptionType.NO:
            return 0
        if option.type == OptionType.CARD:
            return self._score_card_choice(option)
        if option.type == OptionType.PLAY:
            return self._score_play(option)
        if option.type == OptionType.ATTACH:
            return self._score_attach(option)
        if option.type == OptionType.EVOLVE:
            return self._score_evolve(option)
        if option.type == OptionType.ABILITY:
            return self._score_ability(option)
        if option.type == OptionType.RETREAT:
            return 2000 if plan.attacker >= 1 else -1
        if option.type == OptionType.ATTACK:
            return 1100 if (option.attackId == MEGA_BRAVE) == (plan.attack_index == 1) else 1000
        return 0

    def _score_card_choice(self, option) -> float:
        card = get_card(self.obs, option.area, option.index, option.playerIndex)
        if card is None:
            return 0

        if self.context in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
            return self._score_active_choice(option, card)
        if self.context == SelectContext.SETUP_ACTIVE_POKEMON:
            return self._score_setup_active(card)
        if self.context == SelectContext.TO_HAND:
            return self._score_to_hand(card)
        if self.context == SelectContext.ATTACH_FROM and isinstance(card, Pokemon):
            return self._energy_target_score(card, option.area == AreaType.ACTIVE)
        return 0

    def _score_active_choice(self, option, card: Pokemon | Card) -> float:
        if not isinstance(card, Pokemon):
            return 0

        if option.playerIndex != self.my_index:
            return 100 if option.index == plan.target - 1 else 0

        score = len(card.energies) * 2
        if option.index == plan.attacker - 1:
            score += 100
        if card.id == C.MEGA_LUCARIO_EX:
            score += 8 if self.my_prizes_left in {2, 3} else 20
        elif card.id == C.HARIYAMA and len(card.energies) >= 2:
            score += 15
        elif card.id == C.MAKUHITA and len(card.energies) >= 2:
            score += 10
        elif card.id == C.SOLROCK:
            score += 5
        elif card.id == C.RIOLU:
            score += 4
        return score

    def _score_setup_active(self, card: Pokemon | Card) -> int:
        if card.id == C.SOLROCK:
            return 2 if self.state.firstPlayer == self.my_index else 4
        if card.id == C.RIOLU:
            return 3
        if card.id == C.MAKUHITA:
            return 1
        return 0

    def _score_to_hand(self, card: Pokemon | Card) -> float:
        score = 200 - self.hand_counts[card.id] * 100
        if card.id == C.MAKUHITA:
            score += -10 if self.field_counts[card.id] >= 1 else 10
        elif card.id == C.HARIYAMA:
            score += 20 if self.field_counts[C.MAKUHITA] >= 1 else -20
        elif card.id == C.LUNATONE:
            score += -250 if self.field_counts[card.id] >= 1 else 60
        elif card.id == C.SOLROCK:
            score += -250 if self.field_counts[card.id] >= 1 else 50
        elif card.id == C.RIOLU:
            lucario_line = self.field_counts[C.RIOLU] + self.field_counts[C.MEGA_LUCARIO_EX]
            score += -150 if lucario_line >= 2 else -3 if lucario_line >= 1 else 40
        elif card.id == C.MEGA_LUCARIO_EX:
            score += 40 if self.field_counts[C.RIOLU] >= 1 else -15
        elif card.id == C.BASIC_FIGHTING_ENERGY:
            score += 30 if not ability_used or not self.state.energyAttached else -1
        return score

    def _score_play(self, option) -> float:
        card = get_card(self.obs, AreaType.HAND, option.index, self.my_index)
        data = card_table[card.id]
        if data.cardType == CardType.POKEMON:
            return self._score_play_pokemon(card)
        return self._score_play_trainer(card)

    def _score_play_pokemon(self, card: Card) -> float:
        score = 20000
        if card.id in {C.LUNATONE, C.SOLROCK} and self.field_counts[card.id] >= 1:
            return -1
        if card.id == C.RIOLU and self.field_counts[C.RIOLU] + self.field_counts[C.MEGA_LUCARIO_EX] >= 2:
            return -1
        return score

    def _score_play_trainer(self, card: Card) -> float:
        if card.id == C.SWITCH:
            return 6000 if plan.attacker > 0 else -1
        if card.id == C.PREMIUM_POWER_PRO:
            if self.state.supporterPlayed and plan.remain_hp <= 0:
                return -1
            if not self.can_attack:
                can_bridge_draw = (
                    not self.state.supporterPlayed
                    and self.hand_counts[C.CARMINE] > 0
                    and self.hand_counts[C.LILLIE_DETERMINATION] == 0
                    and not self._low_deck()
                )
                return 3050 if can_bridge_draw else -1
            return 5000
        if card.id == C.BOSS_ORDERS:
            return 3200 if plan.target >= 1 else -1
        if card.id == C.CARMINE:
            return -1 if self._low_deck() else 3000
        if card.id == C.LILLIE_DETERMINATION:
            return -1 if self._low_deck() else 3100
        if card.id == C.GRAVITY_MOUNTAIN:
            return self._score_gravity_mountain()
        return 10000

    def _score_gravity_mountain(self) -> float:
        opponent_has_stage2 = any(
            pokemon is not None and card_table[pokemon.id].stage2 for pokemon in self._opponent_board()
        )
        if opponent_has_stage2:
            return 3500
        return 1200 if self.stadium_id else -1

    def _low_deck(self) -> bool:
        return self.me.deckCount <= LOW_DECK_COUNT

    def _score_attach(self, option) -> float:
        card = get_card(self.obs, AreaType.HAND, option.index, self.my_index)
        pokemon = get_card(self.obs, option.inPlayArea, option.inPlayIndex, self.my_index)
        if not isinstance(pokemon, Pokemon):
            return 0

        if card.id == C.HERO_CAPE:
            score = 7000
            if pokemon.id == C.RIOLU:
                score += 100
            elif pokemon.id == C.MEGA_LUCARIO_EX:
                score += 200
            return score

        score = self._energy_target_score(pokemon, option.inPlayArea == AreaType.ACTIVE)
        board_index = option.inPlayIndex if option.inPlayArea == AreaType.ACTIVE else option.inPlayIndex + 1
        if board_index == plan.attacker and plan.needs_energy:
            score += 200
        return score

    def _score_evolve(self, option) -> float:
        pokemon = get_card(self.obs, option.inPlayArea, option.inPlayIndex, self.my_index)
        if not isinstance(pokemon, Pokemon):
            return 0
        if pokemon.id == C.MAKUHITA and plan.target == 0:
            return -1
        return 9000 + len(pokemon.energies)

    def _score_ability(self, option) -> float:
        card = get_card(self.obs, option.area, option.index, self.my_index)
        if card.id == C.LUMIOSE_CITY:
            return 1
        if card.id == C.LUNATONE and self._low_deck():
            return -1
        return 30000

    def _remember_lunatone_ability(self, ranked: list[int]) -> None:
        global ability_used
        if self.context != SelectContext.MAIN or not ranked:
            return
        option = self.select.option[ranked[0]]
        if option.type != OptionType.ABILITY:
            return
        card = get_card(self.obs, option.area, option.index, self.my_index)
        if card is not None and card.id == C.LUNATONE:
            ability_used = True


def _base_agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return my_deck

    global pre_turn
    global ability_used
    global plan

    if pre_turn != obs.current.turn:
        pre_turn = obs.current.turn
        ability_used = False
        plan = AttackPlan()

    return LucarioPolicy(obs).choose()

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


# ===== exp018 prize-liability discipline (non-ex only) =====
_MAX_TREV_LINE = 3
_KEEP_OPEN_SLOT = True

def _bench_free(self):
    return self.me.benchMax - len(self.me.bench)

_CRUSTLE, _DWEBBLE = 345, 344
def _opp_is_wall(self):
    # vs a stall wall (Crustle/Dwebble) we must DEVELOP, not ration the bench
    return any(p is not None and p.id in (_CRUSTLE, _DWEBBLE) for p in self._opponent_board())

_orig_spp = LucarioPolicy._score_play_pokemon
def _disc_score_play_pokemon(self, card):
    if not _DECK_NONEX or _opp_is_wall(self):
        return _orig_spp(self, card)
    cid = card.id
    free = _bench_free(self)
    line = self.field_counts[_TREVENANT] + self.field_counts[_PHANTUMP]
    behind = len(self.me.prize) > len(self.opponent.prize)   # we have MORE prizes left = behind
    base = 20000
    if cid == _PHANTUMP:
        # evolve fuel for Trevenant: want a few, not a flood (each is a 1-prize KO target)
        cap = _MAX_TREV_LINE + (1 if behind else 0)
        if line >= cap:
            return -1
        s = base + (300 if line == 0 else 120 if line == 1 else 40)
        if _KEEP_OPEN_SLOT and free <= 1 and line >= 2:
            s -= 6000                      # keep a slot; we already have attackers
        return s
    if cid == _SNORLAX:                    # 1 benched Snorlax powers Extra Helpings; more = liability
        return -1 if self.field_counts[_SNORLAX] >= 1 else base + 60
    if cid == _CRAMORANT:                  # situational attacker; one is enough
        return -1 if self.field_counts[_CRAMORANT] >= 1 else base + 20
    if cid in (_DUNSPARCE, _DUDUNSPARCE):  # draw engine: want ~1 line, not stacks
        if self.field_counts[_DUNSPARCE] + self.field_counts[_DUDUNSPARCE] >= 2:
            return -1
        return base + 80
    if _KEEP_OPEN_SLOT and free <= 1:      # any other basic: don't fill the last slot
        return base - 4000
    return base
LucarioPolicy._score_play_pokemon = _disc_score_play_pokemon

_ONE_ENERGY = {_TREVENANT, _PHANTUMP, _CRAMORANT}
_orig_ets = LucarioPolicy._energy_target_score
def _disc_energy_target_score(self, pokemon, active):
    if _DECK_NONEX and pokemon.id in _ONE_ENERGY and len(pokemon.energies) >= 2:
        return -1                          # 1-energy attacker already armed -> don't waste energy
    return _orig_ets(self, pokemon, active)
LucarioPolicy._energy_target_score = _disc_energy_target_score


# ===== exp022 Boss's Orders gust fix: reward prize-taking KOs so we gust the bench =====
def _gust_plan_attack(self):
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
                # reward TAKING A PRIZE so a benched KO beats chipping an un-KO-able active
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                sc += 500 if prize >= 1 else 0
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _gust_plan_attack


_rev = {"turn": -2, "last_opp": None, "window": False}

def _rev_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    # revenge window: opponent took a prize since our last turn => a Hop's Pokemon was KO'd
    t = self.state.turn
    cur_opp = len(self.opponent.prize)
    if t != _rev["turn"]:
        _rev["window"] = (_rev["last_opp"] is not None and cur_opp < _rev["last_opp"])
        _rev["last_opp"] = cur_opp
        _rev["turn"] = t
    window = _rev["window"]
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
            # (1) revenge window: Trevenant's Horrifying Revenge does +100 (model as +BONUS)
            if me.id == _TREVENANT and idx == 0 and window:
                dmg += 50
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
                # (2) prize trade: flat +500 for a KO, plus extra for multi-prize (ex) targets
                if prize >= 1:
                    sc += 500 + 0 * (prize - 1)

                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _rev_plan_attack

# (3) backup charge: when the active is armed, charge a benched non-ex attacker for continuity
if 0:
    _orig_ets_bc = LucarioPolicy._energy_target_score
    def _bc_energy_target_score(self, pokemon, active):
        if not active and pokemon.id in (_TREVENANT, _PHANTUMP) and len(pokemon.energies) == 0:
            board = self._my_board()
            act = board[0] if board else None
            if act is not None and len(act.energies) >= 1:
                return 40
        return _orig_ets_bc(self, pokemon, active)
    LucarioPolicy._energy_target_score = _bc_energy_target_score


# ===== exp047 state-conditioned learned DISCARD chooser =====
_SP3_TBL = {11: (-0.18695363402366638, (-0.4801807403564453, 0.3708818554878235, -0.2241823524236679, 0.05088537931442261, 0.050888389348983765, 0.005423860624432564, -0.12541043758392334, -0.1889115869998932, 0.3721727430820465, 0.4334675371646881, 0.07826918363571167, 0.03817075118422508, -1.2174278497695923, -0.18695363402366638)), 19: (-0.25049611926078796, (-0.13387718796730042, 0.7603338360786438, -0.2935282289981842, -0.20859019458293915, -0.19183814525604248, -0.08507005870342255, 0.02210555411875248, -0.29440614581108093, -0.24372409284114838, 0.43574264645576477, 0.45092537999153137, 0.2881888747215271, -0.8192360997200012, -0.25049611926078796)), 304: (-0.14681082963943481, (0.034305140376091, 0.10336332768201828, -0.10344476997852325, -0.030621636658906937, 0.35172155499458313, -0.927772045135498, 0.0391041524708271, -0.12111659348011017, -0.3427104353904724, -0.7508230805397034, 0.06876914948225021, 0.5451961159706116, 0.2016105055809021, -0.14681082963943481)), 311: (0.05580708011984825, (0.27953606843948364, -0.3387906551361084, -0.18122337758541107, -0.05508643388748169, -0.036730021238327026, -0.03470836952328682, 0.22326628863811493, -0.23955488204956055, -0.07428194582462311, 0.2150724232196808, 0.24537022411823273, -0.1534300446510315, 0.024366432800889015, 0.05580708011984825)), 878: (0.05145764350891113, (0.3102457821369171, 0.5855077505111694, -0.3652626872062683, 0.10031654685735703, -0.07254687696695328, 0.4507213830947876, 0.16721540689468384, 0.2920684814453125, 0.09989432245492935, -0.7234624624252319, -0.20947502553462982, -0.7669947147369385, -0.35865068435668945, 0.05145764350891113)), 879: (0.1551545411348343, (0.2819729447364807, -0.47096776962280273, 0.18276691436767578, -0.06378600001335144, -0.05629544332623482, 0.0015702767996117473, -0.27137935161590576, -0.1508619487285614, 0.36865317821502686, 0.050703685730695724, -0.026459598913788795, -0.219310462474823, -0.0660545825958252, 0.1551545411348343)), 1092: (-0.26663467288017273, (-1.0017762184143066, -0.30538210272789, 1.0106240510940552, 0.4993985891342163, 0.5375414490699768, -0.5002366900444031, -0.049072738736867905, -0.4607940912246704, -0.6750863790512085, -1.958350419998169, -0.26663467288017273, 1.6644572019577026, -0.7105402946472168, -0.26663467288017273)), 1097: (0.011489675380289555, (-0.2613862454891205, 0.2984809875488281, -0.23035477101802826, 0.07709600031375885, -0.256777822971344, 1.1641572713851929, 0.6475357413291931, 0.1906704306602478, 0.543890655040741, -0.09724818170070648, -0.012886966578662395, -0.43669024109840393, -0.8366419076919556, 0.011489675380289555)), 1115: (-0.06948456168174744, (0.6756098866462708, -0.5283113121986389, -0.15092779695987701, 0.1826973408460617, 0.25055691599845886, -0.2752092480659485, 0.11295997351408005, 0.10756815969944, -0.07702473551034927, 0.18249870836734772, -0.12073075026273727, 0.13054314255714417, 0.1725921481847763, -0.06948456168174744)), 1122: (0.12466315925121307, (0.7732017040252686, 0.5844656825065613, -0.10752595961093903, -0.07095957547426224, -0.06063435226678848, 0.05012262985110283, -0.7528052926063538, 0.2173461616039276, 0.011372015811502934, -0.1640385389328003, 0.050597261637449265, -0.2716311812400818, 0.45194756984710693, 0.12466315925121307)), 1134: (0.11922476440668106, (0.0010156852658838034, -0.04898181930184364, 0.2220732420682907, -0.09131760895252228, -0.03338668867945671, -0.4051191806793213, 0.007563178427517414, 0.26650822162628174, -0.36115285754203796, 0.13075779378414154, 0.11921460181474686, -0.05726214498281479, -0.012385893613100052, 0.11922476440668106)), 1152: (-0.02864866517484188, (-0.5466741919517517, 0.2786993384361267, -0.11068682372570038, 0.3129003345966339, 0.16147883236408234, 0.02404380962252617, 0.5268256664276123, -0.3737616539001465, 0.10850561410188675, -0.48899781703948975, -0.056525565683841705, -0.498947411775589, 0.4252011477947235, -0.02864866517484188)), 1171: (-0.054158516228199005, (-0.7606934309005737, -0.5655937194824219, 0.12456569820642471, 0.15914812684059143, 0.16847103834152222, -0.12276364117860794, -0.40868857502937317, -0.0854688212275505, 0.18672512471675873, -0.16215123236179352, -0.09792610257863998, -0.23427577316761017, 1.2748368978500366, -0.054158516228199005)), 1182: (0.11390869319438934, (-0.8372933864593506, 0.09123198688030243, -0.02696032077074051, -0.11672468483448029, -0.22636756300926208, 0.6237540245056152, 0.24231505393981934, -0.4133002460002899, 0.118404820561409, 0.05380642041563988, 0.24997130036354065, 0.4257700741291046, 0.013698991388082504, 0.11390869319438934)), 1197: (-0.06369514018297195, (-0.18695546686649323, -0.2707926332950592, 0.06570521742105484, 0.047895610332489014, 0.03390733525156975, 0.028004029765725136, 0.3758091628551483, -0.18095599114894867, 0.5769231915473938, 0.11708617210388184, -0.07726718485355377, 0.07547136396169662, 0.02346518449485302, -0.06369514018297195)), 1219: (0.026673873886466026, (0.3306347131729126, 0.05790122598409653, -0.0779605582356453, 0.16269804537296295, 0.1673785001039505, -0.10763964056968689, -0.2465706467628479, 0.11451791971921921, 0.2653655409812927, -0.10471490025520325, -0.06583573669195175, 0.03849414363503456, -0.18243452906608582, 0.026673873886466026)), 1225: (0.10023920238018036, (-0.4221024513244629, 0.1491953283548355, 0.07913939654827118, -0.011304805055260658, -0.07223760336637497, 0.4908888339996338, 0.4176497757434845, -0.11885754764080048, -0.12631180882453918, -0.12327758222818375, -0.30866867303848267, -0.12058713287115097, 0.8319752216339111, 0.10023920238018036)), 1227: (-0.11676435172557831, (0.39983442425727844, 0.10314550995826721, 0.312322735786438, 0.18765904009342194, 0.17906087636947632, -0.10254353284835815, -0.3209620714187622, 0.24553720653057098, -0.15759402513504028, 0.18619073927402496, -0.17395836114883423, 0.030597589910030365, 0.4489644467830658, -0.11676435172557831)), 1255: (0.028976967558264732, (0.24001485109329224, -0.039795778691768646, 0.05350605398416519, -0.22215209901332855, -0.17012746632099152, -0.4241197109222412, -0.011251566000282764, 0.5593460202217102, -0.20158998668193817, 0.07168406993150711, 0.15446431934833527, 0.08033691346645355, -0.09632208943367004, 0.028976967558264732))}
_SP3_U = (0.161019429564476, -0.20379287004470825, -0.4654447138309479)
_SP3_STOP_B = 0.0
_SP3_STOP_W = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
_sp3_orig_choose = LucarioPolicy.choose

def _sp3_feats(self):
    me, op = self.me, self.opponent
    board = self._my_board()
    act = board[0] if board else None
    line = self.field_counts[_TREVENANT] + self.field_counts[_PHANTUMP]
    return (
        min(self.state.turn, 30) / 30.0,
        len(me.hand) / 10.0,
        me.deckCount / 60.0,
        len(me.prize) / 6.0,
        len(op.prize) / 6.0,
        (len(me.prize) - len(op.prize)) / 6.0,
        len(me.bench) / 5.0,
        len(op.bench) / 5.0,
        line / 4.0,
        1.0 if self.state.energyAttached else 0.0,
        1.0 if self.state.supporterPlayed else 0.0,
        1.0 if (act is not None and act.id in (_TREVENANT, _PHANTUMP)) else 0.0,
        min(len(act.energies) if act is not None else 0, 3) / 3.0,
        1.0,
    )

def _sp3_choose(self):
    if self.context != SelectContext.DISCARD or not self.select.option:
        return _sp3_orig_choose(self)
    cids = []
    for option in self.select.option:
        card = get_card(self.obs, option.area, option.index, option.playerIndex)
        cid = getattr(card, "id", None)
        if cid is None or cid not in _SP3_TBL:
            return _sp3_orig_choose(self)   # unknown card -> conservative fallback
        cids.append(cid)
    f = _sp3_feats(self)
    scores = []
    for cid in cids:
        b, w = _SP3_TBL[cid]
        s = b + sum(wi * fi for wi, fi in zip(w, f))
        s += (_SP3_U[0] * min(self.hand_counts[cid], 3) / 3.0
              + _SP3_U[1] * min(self.field_counts[cid], 3) / 3.0
              + _SP3_U[2] * min(self.discard_counts[cid], 3) / 3.0)
        scores.append(s)
    stop = _SP3_STOP_B + sum(wi * fi for wi, fi in zip(_SP3_STOP_W, f))
    remaining = sorted(range(len(cids)), key=lambda i: -scores[i])
    out = []
    for i in remaining:
        if len(out) >= self.select.maxCount:
            break
        if len(out) >= self.select.minCount and scores[i] <= stop:
            break                            # model prefers STOP over this pick
        out.append(i)
    if len(out) < self.select.minCount:
        return _sp3_orig_choose(self)
    return out
LucarioPolicy.choose = _sp3_choose


# ===== turn-beam: verified full-turn sequencing (exp035) =====
import dataclasses as _tb_dc
import random as _tb_random
from collections import Counter as _tb_Counter
from cg import api as _tb_api

_TB_K = 2
_TB_BEAM = 5
_TB_BRANCH = 10
_TB_MAXSTEPS = 900
_TB_DMG_MIN = 30
_TB_STATS = {"planned": 0, "fired": 0, "errors": 0}
_tb_rng = _tb_random.Random(20260704)
_tb_inner = _base_agent

# ===== exp045 TB_VALUE: learned terminal evaluator replaces the damage tiebreak =====
# When enabled, outcome()'s SECOND key becomes int(1000*V(end-of-turn state)) from
# exp032/033's 17-feature value MLP (mid-game AUC 0.806) instead of raw damage
# dealt; the FIRST key (prizes taken this turn, +100 on win) is unchanged, so
# "take prizes when you can" is preserved and only no-prize-turn planning changes.
# This targets the exp044-diagnosed blind spot: the damage tiebreak prefers
# chipping a 320hp Dragapult ex over evolution-line denial / setup quality.
_TB_VALUE = 0
if _TB_VALUE:
    import numpy as _tb_np
    _tb_vz = _tb_np.load('/home/jun/kaggle-ptcg-ai-battle/workspace/exp032_valuescale/value_mlp2.npz')
    _TB_DMG_MIN = 20     # margin now in value-milliunits

    def _tb_value(cur, my):
        me, opp = cur.players[my], cur.players[1 - my]
        def _e(m):
            e = getattr(m, "energyCards", None)
            if isinstance(e, list):
                return len(e)
            e = getattr(m, "energies", None)
            return sum(e) if isinstance(e, list) else 0
        def _ahp(p):
            a = p.active or []
            if a and a[0] is not None:
                mh = getattr(a[0], "maxHp", 0) or 0
                return (getattr(a[0], "hp", 0) / mh) if mh else 0.0
            return 0.0
        def _aene(p):
            a = p.active or []
            return _e(a[0]) if a and a[0] is not None else 0
        def _bene(p):
            return sum(_e(m) for m in list(p.active or []) + list(p.bench or []) if m is not None)
        def _st(p):
            a = p.active or []
            if not (a and a[0] is not None):
                return 0
            return sum(int(bool(getattr(p, k, False))) for k in
                       ("asleep", "confused", "paralyzed", "poisoned", "burned"))
        pm, po = len(me.prize), len(opp.prize)
        f = [po - pm, pm, po, _ahp(me), _ahp(opp), _aene(me), _aene(opp),
             _bene(me), _bene(opp), len(me.bench or []), len(opp.bench or []),
             me.handCount, opp.handCount, me.deckCount,
             cur.turn, int(cur.firstPlayer == my), _st(opp)]
        z = (_tb_np.asarray(f, dtype=_tb_np.float64) - _tb_vz["mean"]) / _tb_vz["std"]
        h = _tb_np.maximum(z @ _tb_vz["W0"] + _tb_vz["b0"], 0)
        h = _tb_np.maximum(h @ _tb_vz["W1"] + _tb_vz["b1"], 0)
        return float(1 / (1 + _tb_np.exp(-(h @ _tb_vz["W2"] + _tb_vz["b2"])[0])))


def _tb_clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _tb_card_ids(cards):
    return [c.id for c in cards or [] if c is not None and getattr(c, "id", None) is not None]


def _tb_mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _tb_card_ids([m])
        out += _tb_card_ids(getattr(m, "preEvolution", None))
        out += _tb_card_ids(getattr(m, "energyCards", None) or [])
        out += _tb_card_ids(getattr(m, "tools", None))
    return out


def _tb_board_hp(p):
    tot = 0
    for m in list(p.active or []) + list(p.bench or []):
        if m is not None:
            tot += getattr(m, "hp", 0) or 0
    return tot


def _tb_det(me, opp):
    rem = _tb_Counter(my_deck)
    rem.subtract(_tb_Counter(_tb_card_ids(me.hand) + _tb_mon_ids(me.active)
                             + _tb_mon_ids(me.bench) + _tb_card_ids(me.discard)))
    pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
    if len(pool) < me.deckCount + len(me.prize):
        pool = list(my_deck)
    _tb_rng.shuffle(pool)
    opool = _tb_mon_ids(opp.active) + _tb_mon_ids(opp.bench) + _tb_card_ids(opp.discard)
    if not opool:
        opool = list(my_deck)
    samp = lambda k: [opool[_tb_rng.randrange(len(opool))] for _ in range(k)]
    return dict(your_deck=pool[: me.deckCount],
                your_prize=pool[me.deckCount: me.deckCount + len(me.prize)],
                opponent_deck=samp(opp.deckCount),
                opponent_prize=samp(len(opp.prize)),
                opponent_hand=samp(opp.handCount),
                opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])


def _tb_beam_once(obs, my):
    me0 = obs.current.players[my]
    opp0 = obs.current.players[1 - my]
    opp_prize0, opp_hp0 = len(opp0.prize), _tb_board_hp(opp0)
    root = _tb_api.search_begin(obs, **_tb_det(me0, opp0))
    steps = 0

    def outcome(ss):
        cur = ss.observation.current
        if cur is None:
            return (-1, 0)
        pz = opp_prize0 - len(cur.players[1 - my].prize)
        if _TB_VALUE:
            dmg = int(1000 * _tb_value(cur, my))
        else:
            dmg = max(0, opp_hp0 - _tb_board_hp(cur.players[1 - my]))
        if cur.result == my:
            pz += 100
        elif cur.result != -1:
            return (-1, 0)
        return (pz, dmg)

    try:
        # base line (post-revenge inner policy) within the same determinization
        ss = root
        for _ in range(40):
            o = ss.observation
            cur = o.current
            if cur is None or cur.result != -1 or o.select is None or cur.yourIndex != my:
                break
            try:
                ss = _tb_api.search_step(ss.searchId, _tb_clamp(_tb_inner(_tb_dc.asdict(o)), o.select))
            except Exception:
                break
        base_pz, base_dmg = outcome(ss)

        frontier = [(root, None, False)]
        best = {}
        for _depth in range(24):
            nxt = []
            for st, first, done in frontier:
                o = st.observation
                cur = o.current
                ended = (done or cur is None or cur.result != -1
                         or o.select is None or cur.yourIndex != my)
                if ended:
                    if first is not None:
                        pz = outcome(st)
                        if pz > best.get(first, (-1, 0)):
                            best[first] = pz
                    continue
                n = len(o.select.option)
                if o.select.maxCount != 1:
                    idxs = [_tb_clamp(list(range(o.select.minCount)), o.select)]
                else:
                    idxs = [[i] for i in range(min(n, _TB_BRANCH))]
                for sel in idxs:
                    if steps >= _TB_MAXSTEPS:
                        break
                    try:
                        child = _tb_api.search_step(st.searchId, sel)
                    except Exception:
                        continue
                    steps += 1
                    f = first if first is not None else (sel[0] if len(sel) == 1 else None)
                    nxt.append((child, f, False))
            if not nxt or steps >= _TB_MAXSTEPS:
                break
            nxt.sort(key=lambda t: outcome(t[0]), reverse=True)
            frontier = nxt[:_TB_BEAM]
        for st, first, _d in frontier:
            if first is not None and st.observation.current is not None:
                pz = outcome(st)
                if pz > best.get(first, (-1, 0)):
                    best[first] = pz
        return best, base_pz, base_dmg
    finally:
        try:
            _tb_api.search_end()
        except Exception:
            pass


def _base_agent(obs_dict):
    sel_out = _tb_inner(obs_dict)
    try:
        obs = to_observation_class(obs_dict)
        select = obs.select
        if (select is None or select.maxCount != 1 or len(select.option) <= 1
                or select.context != _tb_api.SelectContext.MAIN):
            return sel_out
        base_sel = _tb_clamp(sel_out, select)
        my = obs.current.yourIndex
        _TB_STATS["planned"] += 1
        _rev_save = dict(_rev)            # revenge cross-turn tracker: shield from
        try:                              # imagined states seen during search
            qualify = None
            for _ in range(_TB_K):
                b, base_pz, base_dmg = _tb_beam_once(obs, my)
                det_q = {}
                for a, (pz, dmg) in b.items():
                    if pz > base_pz or (pz == base_pz and dmg >= base_dmg + _TB_DMG_MIN):
                        det_q[a] = (pz - base_pz, dmg - base_dmg)
                if qualify is None:
                    qualify = det_q
                else:
                    qualify = {a: min(m, det_q[a]) for a, m in qualify.items() if a in det_q}
                if not qualify:
                    return base_sel
        finally:
            _rev.clear()
            _rev.update(_rev_save)
        if qualify:
            best_a = max(qualify, key=qualify.get)
            if best_a != base_sel[0]:
                _TB_STATS["fired"] += 1
                return [best_a]
    except Exception:
        _TB_STATS["errors"] += 1
    return sel_out



# ===== crash-safety wrapper =====
def _legal_fallback(select):
    n=len(select.option)
    return [] if n==0 else list(range(min(max(1,select.minCount),n)))
def _valid(sel,select):
    n=len(select.option)
    if not isinstance(sel,list) or any((not isinstance(i,int)) or i<0 or i>=n for i in sel): return False
    if len(set(sel))!=len(sel): return False
    return select.minCount<=len(sel)<=select.maxCount
def agent(obs_dict):
    try: obs=to_observation_class(obs_dict)
    except Exception:
        return list(my_deck) if obs_dict.get("select") is None else [0]
    if obs.select is None: return list(my_deck)
    try:
        sel=_base_agent(obs_dict)
        return sel if _valid(sel,obs.select) else _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
