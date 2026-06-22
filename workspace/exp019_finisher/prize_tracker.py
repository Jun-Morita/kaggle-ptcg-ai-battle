"""Conservative prize-card tracker (exp019).

Adapted from the public Gold(~LB1250) Starmie writeup's PrizeTracker
(references/knowledge/prize_tracking_starmie_0622.md; public, attribution). Purpose:
feed the forward-search the CORRECT available deck so it cannot "imagine" a card
that is actually face-down in our prizes (the NOMATCH / false-lethal bug that sank
exp015). Principle: a WRONG prize inference is worse than none -> return unknown
when ambiguous.

When a search effect makes our whole deck visible (obs.select.deck), we deduce
prized = decklist - everything-visible, cache it, and thereafter expose the exact
deck contents (decklist - visible - prized) for determinization.
"""
from __future__ import annotations
from collections import Counter


class PrizeTracker:
    def __init__(self, decklist):
        self.decklist = list(decklist)
        self._prized = None  # Counter or None (None = unknown)

    def reset(self):
        self._prized = None

    def _unseen(self, obs):
        """Counter(decklist) minus everything visible EXCEPT the deck = deck + prize."""
        yi = obs.current.yourIndex
        p = obs.current.players[yi]
        rem = Counter(self.decklist)

        def sub(c):
            if c is not None and getattr(c, "id", None) is not None and rem[c.id] > 0:
                rem[c.id] -= 1

        for c in (p.hand or []):
            sub(c)
        for mon in list(p.active or []) + list(p.bench or []):
            if mon is None:
                continue
            sub(mon)
            for c in getattr(mon, "preEvolution", None) or []:
                sub(c)
            for c in getattr(mon, "energyCards", None) or []:
                sub(c)
            for c in getattr(mon, "tools", None) or []:
                sub(c)
        for c in (p.discard or []):
            sub(c)
        for c in (obs.current.stadium or []):
            if c is not None and getattr(c, "playerIndex", None) == yi:
                sub(c)
        # in-flight effect card (e.g. Hilda left hand, not yet in discard)
        sel = obs.select
        eff = getattr(sel, "effect", None) if sel is not None else None
        if eff is not None and getattr(eff, "playerIndex", None) == yi:
            sub(eff)
        return rem

    def update(self, obs):
        """Deduce the prized set when the deck is fully visible (during a search)."""
        sel = obs.select
        if sel is None or getattr(sel, "deck", None) is None:
            return
        yi = obs.current.yourIndex
        p = obs.current.players[yi]
        if len(sel.deck) != p.deckCount:
            return
        unseen = self._unseen(obs)  # deck + prize
        for c in sel.deck:          # subtract the visible deck -> leaves prize
            if c is not None and getattr(c, "id", None) is not None and unseen[c.id] > 0:
                unseen[c.id] -= 1
        if any(v < 0 for v in unseen.values()):
            return
        prized = Counter({k: v for k, v in unseen.items() if v > 0})
        if sum(prized.values()) != len(p.prize):
            return
        self._prized = prized

    def prized(self):
        return None if self._prized is None else self._prized.copy()

    def deck_contents(self, obs):
        """Exact multiset of cards currently in our DECK (decklist - visible - prized),
        or None if the prize set is unknown / inconsistent."""
        if self._prized is None:
            return None
        yi = obs.current.yourIndex
        p = obs.current.players[yi]
        unseen = self._unseen(obs)          # deck + prize
        unseen.subtract(self._prized)       # - prize -> deck
        if any(v < 0 for v in unseen.values()):
            return None
        cards = []
        for cid, cnt in unseen.items():
            cards.extend([cid] * cnt)
        if len(cards) != p.deckCount:
            return None
        return cards
