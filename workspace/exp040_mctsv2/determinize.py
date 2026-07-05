"""Exclusion-based determinization for exp040's self-play MCTS.

Fixes exp004's known bug (`train_mcts.py:407-410`, see SESSION_NOTES): the official
sample's `mcts_agent` filled the opponent's hidden deck/hand/prize with a placeholder
card (Snorlax id 1072 / basic energy id 1), so MCTS planned against a fantasy
opponent and never saw real threats (dragapult/lucario). This module replaces that
with exclusion sampling: draw the missing cards from (decklist - everything visible)
so the search can never imagine a card that's actually in a visible zone.

Self-play here always uses BOTH decks in their exact, known form (the trainee's
own deck, and the teacher's deck -- whichever pool matchup was sampled for this
game): unlike exp038/exp039's OpponentModel (built for when the opponent's real
decklist is UNKNOWN and must be guessed from archetype detection), no detection
is needed here since we chose both decks ourselves. `my_deck`/`opp_deck` may
therefore be the same list (mirror) or different (teacher_pool.py's diverse
matchups) -- the caller just passes whichever is correct for that seat.
Reused pattern: workspace/exp039_guardopp/guard_opp_policy.py's
`_card_ids` / `_mon_ids` / `our_deck_sample` / `det`.
"""
from __future__ import annotations
import random
from collections import Counter


def _card_ids(cards):
    out = []
    for c in cards or []:
        cid = getattr(c, "id", None)
        if cid is not None:
            out.append(cid)
    return out


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None))
        out += _card_ids(getattr(m, "tools", None))
    return out


def _extra_visible_cards(obs):
    """Cards visible outside hand/board/discard: stadium in play, the card
    mid-resolution (select.effect), and the card a select is asking about
    (select.contextCard). Each entry carries its own `.playerIndex`; filtered
    per-player by the caller.

    Deliberately NOT included: `state.looking` / `select.deck` (cards revealed
    by a deck-peek/search effect, e.g. this deck's Ultra Ball/Poké Pad). Tried
    it -- made conservation WORSE (32/75 -> 123/136 decision points off), because
    those zones can reveal the deck's FULL remaining contents while `deckCount`
    still expects to independently sample that many cards; marking them
    "visible" without changing the needed-count formula creates a shortfall
    that trips the full-deck fallback almost every time (this deck searches
    its own deck very often). Properly handling it means pinning the exact
    known identities into `your_deck` instead of re-sampling -- deferred (see
    SESSION_NOTES); the single-card sources below are net-positive as measured.
    """
    state = obs.current
    out = list(state.stadium or [])
    sel = obs.select
    if sel is not None:
        eff = getattr(sel, "effect", None)
        if eff is not None:
            out.append(eff)
        ctx = getattr(sel, "contextCard", None)
        if ctx is not None:
            out.append(ctx)
    return out


def _visible_ids(player, include_hand, player_index, extra_cards):
    ids = _mon_ids(player.active) + _mon_ids(player.bench) + _card_ids(player.discard)
    if include_hand:
        ids += _card_ids(player.hand)
    counts = Counter(ids)
    # Use max(), not +=: the engine can transiently report a card in one of the
    # "extra" zones WHILE it still appears in hand/board/discard for one frame
    # (e.g. mid-evolution, or a deck-peek revealing a card still physically in
    # the deck pile) -- adding unconditionally would double-count a card
    # that's already tallied and manufacture a phantom extra copy (observed:
    # Hariyama tallied 3x when the deck only has 2 -- exp040/SESSION_NOTES).
    for c in extra_cards:
        if getattr(c, "playerIndex", None) == player_index:
            counts[c.id] = max(counts[c.id], 1)
    return list(counts.elements())


def _sample_unseen_pool(deck, visible_ids, needed, rng):
    rem = Counter(deck)
    rem.subtract(Counter(visible_ids))
    pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
    if len(pool) < needed:
        # inconsistent visible-card count (shouldn't happen with a well-formed
        # decklist) -- fall back to the full deck rather than crash or starve
        # search_begin of enough cards.
        pool = list(deck)
    rng.shuffle(pool)
    return pool


def determinize(obs, your_index, my_deck, opp_deck, pokemon_ids, rng=None):
    """Build the search_begin determinization kwargs for one player's turn.

    `obs` = the Observation (has `.current` = State with `.players[0]`/`.players[1]`
    each a PlayerState, and `.select.effect` for the in-flight resolution card).
    `my_deck` / `opp_deck` = the exact 60-card decklists for the acting player and
    their opponent (may be the same list for a mirror, or different -- e.g.
    teacher_pool.py's diverse matchups; both are always exactly KNOWN here, no
    archetype detection needed, since self-play always chooses both decks itself).
    `pokemon_ids` = set of cardIds with cardType==POKEMON across the whole card
    database (the engine requires `opponent_active`, when supplied, to be a real
    Pokemon id -- exp004's placeholder always used Snorlax=1072 for exactly this
    reason; we must honor the same constraint when sampling a replacement).
    Returns dict(your_deck=..., your_prize=..., opponent_deck=..., opponent_prize=...,
    opponent_hand=..., opponent_active=...) -- same kwarg names exp004's
    `search_begin` call already used, so this is a drop-in replacement.
    """
    rng = rng or random
    state = obs.current
    extra_cards = _extra_visible_cards(obs)
    me = state.players[your_index]
    opp = state.players[1 - your_index]

    # Our own deck pile vs our own prize cards are BOTH face-down to us (PTCG:
    # you don't know your own prizes either) -- sample both from one pool.
    my_visible = _visible_ids(me, True, your_index, extra_cards)
    my_needed = me.deckCount + len(me.prize)
    my_pool = _sample_unseen_pool(my_deck, my_visible, my_needed, rng)
    your_deck = my_pool[: me.deckCount]
    your_prize = my_pool[me.deckCount: me.deckCount + len(me.prize)]

    # Opponent: hand is genuinely hidden -> included in the sampled pool (not
    # subtracted as "visible"). Active is only unknown if face-down (rare
    # mid-search case the official sample also special-cased).
    active = opp.active
    active_unknown = len(active) > 0 and active[0] is None
    opp_visible = _visible_ids(opp, False, 1 - your_index, extra_cards)
    opp_needed = opp.deckCount + len(opp.prize) + opp.handCount + (1 if active_unknown else 0)
    opp_pool = _sample_unseen_pool(opp_deck, opp_visible, opp_needed, rng)

    opponent_active = []
    if active_unknown:
        for i, cid in enumerate(opp_pool):
            if cid in pokemon_ids:
                opponent_active = [opp_pool.pop(i)]
                break
        else:
            # no Pokemon left unaccounted for (shouldn't happen with a legal
            # decklist) -- fall back to any Pokemon in the full decklist.
            fallback = next((cid for cid in opp_deck if cid in pokemon_ids), None)
            opponent_active = [fallback] if fallback is not None else []

    c = 0

    def take(k):
        nonlocal c
        out = opp_pool[c: c + k]
        c += k
        return out

    opponent_deck = take(opp.deckCount)
    opponent_prize = take(len(opp.prize))
    opponent_hand = take(opp.handCount)

    return dict(your_deck=your_deck, your_prize=your_prize,
                opponent_deck=opponent_deck, opponent_prize=opponent_prize,
                opponent_hand=opponent_hand, opponent_active=opponent_active)
