"""Dedicated Crustle anti-ex control policy (exp009).

v004 failed (LB 627) because the generic lucario_v2 policy can't pilot a control
deck: it doesn't recognize Crustle's attack, mismanages healing, and decks out.
This is a purpose-built policy for the Crustle control deck:

  game plan: bench Dwebble (Buddy-Buddy Poffin) -> evolve to Crustle ->
  attach energy + Hero's Cape (250+ HP wall, immune to ex) -> attack Superb
  Scissors (120) every turn -> heal (Jumbo Ice Cream / Cook) to never die ->
  draw with Lillie, avoid decking out.

Context-aware option scoring; crash-safe; returns legal selections. Designed to
be inlined into a submission main.py (reads its deck from deck.csv / my_deck).
"""
from __future__ import annotations

import os

from cg.api import (
    AreaType, CardType, OptionType, SelectContext, SelectType,
    all_card_data, to_observation_class,
)

_CARD = {c.cardId: c for c in all_card_data()}

# key card ids (this deck)
DWEBBLE = 344
CRUSTLE = 345
BUDDY_POFFIN = 1086
JUMBO_ICE_CREAM = 1147
COOK = 1212
LILLIE = 1227
WAITRESS = 1235
HEROS_CAPE = 1159

DECK_PATH = "deck.csv"
if not os.path.exists(DECK_PATH):
    DECK_PATH = "/kaggle_simulations/agent/deck.csv"
with open(DECK_PATH) as _f:
    my_deck = [int(x) for x in _f.read().splitlines() if x.strip()]


def _is_basic_pokemon(cid):
    c = _CARD.get(cid)
    return bool(c and c.cardType == CardType.POKEMON and c.basic)


def _energy_count(poke):
    return len(poke.energies) if poke else 0


def _active(ps):
    return ps.active[0] if ps.active and ps.active[0] else None


def _hand_card_id(obs, idx):
    h = obs.current.players[obs.current.yourIndex].hand
    if h and 0 <= idx < len(h):
        return h[idx].id
    return None


def _get_card(obs, area, index, player_index):
    ps = obs.current.players[player_index]
    try:
        if area == AreaType.HAND:
            return ps.hand[index]
        if area == AreaType.ACTIVE:
            return ps.active[index]
        if area == AreaType.BENCH:
            return ps.bench[index]
        if area == AreaType.DISCARD:
            return ps.discard[index]
        if area == AreaType.DECK and obs.select.deck:
            return obs.select.deck[index]
    except Exception:
        return None
    return None


def _score_main(obs, opt):
    """Score a MAIN option. Higher = do it earlier in the turn."""
    me = obs.current.players[obs.current.yourIndex]
    active = _active(me)
    t = opt.type
    if t == OptionType.ABILITY:
        return 95
    if t == OptionType.EVOLVE:
        # evolving (Dwebble -> Crustle) is top priority
        card = _get_card(obs, opt.area, opt.index, obs.current.yourIndex)
        return 90 if (card and card.id == DWEBBLE) else 80
    if t == OptionType.ATTACH:
        # attach energy, prefer toward an attacker that still needs it
        return 70
    if t == OptionType.PLAY:
        cid = _hand_card_id(obs, opt.index)
        if cid == BUDDY_POFFIN:
            # get Dwebble out if we lack board
            n_line = sum(1 for p in ([active] + list(me.bench)) if p and p.id in (DWEBBLE, CRUSTLE))
            return 85 if n_line < 3 else 20
        if cid in (JUMBO_ICE_CREAM, COOK):
            # heal only when the active is actually damaged
            if active and active.hp < active.maxHp - 20:
                return 88
            return 5
        if cid == HEROS_CAPE:
            # tool on Crustle (more HP) if it has none
            if active and active.id == CRUSTLE and not active.tools:
                return 75
            return 15
        if cid == LILLIE:
            # draw when hand is low, but not when deck is dangerously low
            if me.deckCount <= 7:
                return 3
            return 60 if me.handCount <= 3 else 25
        if cid == WAITRESS:
            return 55 if me.deckCount > 7 else 4
        return 30
    if t == OptionType.ATTACK:
        return 50  # attack near end of turn (after development)
    if t == OptionType.RETREAT:
        return 8
    if t == OptionType.END:
        return 1
    return 20


def _score_card_choice(obs, opt):
    """Score a CARD-selection option by context (search/discard/heal/etc.)."""
    ctx = obs.select.context
    card = _get_card(obs, opt.area, opt.index, opt.playerIndex if opt.playerIndex is not None else obs.current.yourIndex)
    cid = card.id if card else None
    c = _CARD.get(cid)
    # contexts where we want to KEEP/GET the Crustle line or energy
    want_line = ctx in (SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON,
                        SelectContext.TO_ACTIVE, SelectContext.TO_BENCH, SelectContext.TO_FIELD,
                        SelectContext.TO_HAND, SelectContext.EVOLVES_FROM, SelectContext.EVOLVES_TO)
    discard_like = ctx in (SelectContext.DISCARD, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM,
                           SelectContext.DISCARD_CARD_OR_ATTACHED_CARD)
    if cid is None:
        return 0
    if want_line:
        if cid in (DWEBBLE, CRUSTLE):
            return 100
        if c and c.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
            return 60
        return 40
    if discard_like:
        # discard least useful: prefer extra energy / duplicate trainers, keep Pokemon line
        if cid in (DWEBBLE, CRUSTLE):
            return -100
        if c and c.cardType in (CardType.BASIC_ENERGY,):
            return 50
        return 20
    # heal/target/effect contexts: prefer our Crustle / active
    if ctx in (SelectContext.HEAL, SelectContext.ATTACH_FROM, SelectContext.EFFECT_TARGET):
        return 100 if cid == CRUSTLE else 50
    return 40


def _choose(obs):
    select = obs.select
    n = len(select.option)
    st = select.type
    options = select.option

    if st == SelectType.MAIN:
        scores = [_score_main(obs, o) for o in options]
    elif st in (SelectType.CARD, SelectType.ATTACHED_CARD, SelectType.CARD_OR_ATTACHED_CARD,
                SelectType.ENERGY):
        scores = [_score_card_choice(obs, o) for o in options]
    elif st == SelectType.ATTACK:
        # only one real attacker; pick the highest-damage attack option
        scores = []
        for o in options:
            scores.append(100)  # all attack options fine; first is usually the main
    elif st == SelectType.YES_NO:
        # context-driven yes/no
        ctx = select.context
        yes_good = ctx in (SelectContext.IS_FIRST, SelectContext.ACTIVATE,
                           SelectContext.COIN_HEAD, SelectContext.FIRST_EFFECT)
        scores = []
        for o in options:
            if o.type == OptionType.YES:
                scores.append(60 if yes_good else 40)
            elif o.type == OptionType.NO:
                scores.append(40 if yes_good else 60)
            else:
                scores.append(10)
        if ctx == SelectContext.MULLIGAN:  # never voluntarily mulligan away a hand
            for i, o in enumerate(options):
                scores[i] = 60 if o.type == OptionType.NO else 40
    else:
        scores = [50] * n  # COUNT, SKILL, SPECIAL_CONDITION, etc.

    order = sorted(range(n), key=lambda i: -scores[i])
    mn, mx = select.minCount, select.maxCount
    k = mx if mx >= 1 else 0
    # for optional (mn==0) MAIN-style picks we still take the top action;
    # but for multi-select non-main, take up to maxCount of positive-scored.
    if st == SelectType.MAIN:
        chosen = [order[0]] if (k >= 1) else []
    else:
        chosen = []
        for i in order:
            if len(chosen) >= mx:
                break
            if scores[i] <= 0 and len(chosen) >= mn:
                break
            chosen.append(i)
        while len(chosen) < mn and len(chosen) < n:
            for i in order:
                if i not in chosen:
                    chosen.append(i)
                    break
    return chosen


def _legal_fallback(select):
    n = len(select.option)
    return [] if n == 0 else list(range(min(max(1, select.minCount), n)))


def agent(obs_dict):
    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        return list(my_deck) if obs_dict.get("select") is None else [0]
    if obs.select is None:
        return list(my_deck)
    try:
        sel = _choose(obs)
        n = len(obs.select.option)
        if (isinstance(sel, list) and all(0 <= i < n for i in sel) and len(set(sel)) == len(sel)
                and obs.select.minCount <= len(sel) <= obs.select.maxCount):
            return sel
        return _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
