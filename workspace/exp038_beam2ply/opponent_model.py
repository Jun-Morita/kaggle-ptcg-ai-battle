"""exp038 — archetype-matched opponent model for minimax move ranking.

Design review finding: opp_mode="minimax" was ranking the OPPONENT's candidate
moves using OUR OWN deck's policy (revenge_policy, tuned for Hop's Trevenant
scoring) — a mismatch when the opponent runs Lucario/Dragapult/Crustle/etc. This
detects the opponent's archetype from what we've actually seen (active + bench +
discard card ids — NOT their full decklist, which we never see live) via
fine_classify's signature-card classifier, and returns:
  - their REAL 3rd-party pilot code, when we have it (Archaludon, Dragapult, the
    Great Tusk LO agent) — the truest available model of their behavior;
  - our own generic pilot loaded with THEIR known decklist (Crustle, Lucario,
    Grimmsnarl), when we only have the deck, not their pilot;
  - our own deck's pilot as a last-resort fallback (status quo), for genuinely
    unrecognized archetypes or (very common) early turns before enough signature
    cards are revealed for classify() to identify anything — this degrades
    gracefully, same spirit as exp034's board-presence archetype checks.

Detection necessarily improves over the course of a game as more of the
opponent's board/discard becomes visible; it is re-run every call (cheap: pure
set lookups) and the underlying agent instance is cached per detected archetype
to avoid rebuilding it every decision.
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in ("exp001_harness", "exp007_anti_crustle", "exp011_meta_watch",
          "exp020_deckinnov", "exp023_revenge", "exp025_unkoable", "exp030_lomill"):
    sp = os.path.join(ROOT, "workspace", p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from fine_classify import classify  # noqa


def _card_ids(cards):
    return [c.id for c in cards or [] if c is not None and getattr(c, "id", None) is not None]


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None) or [])
        out += _card_ids(getattr(m, "tools", None))
    return out


def visible_ids(player):
    """Card ids we've actually seen from this player's board + discard (partial
    information — never their full decklist)."""
    return set(_mon_ids(player.active) + _mon_ids(player.bench) + _card_ids(player.discard))


_DRAGAPULT_DECK_CSV = os.path.join(ROOT, "references", "raw", "public_notebooks", "dragapult", "deck.csv")
_ARCHALUDON_DECK_CSV = os.path.join(ROOT, "workspace", "exp025_unkoable", "archaludon_opp", "deck.csv")
_LO_DECK_CSV = os.path.join(ROOT, "workspace", "exp030_lomill", "lo_agent", "deck.csv")
_GRIMMSNARL_DECK_JSON = os.path.join(ROOT, "workspace", "exp028_debauchery", "grimmsnarl_deck.json")


def _read_deck_csv(path):
    return [int(x) for x in open(path).read().split() if x.strip().isdigit()]


class OpponentModel:
    """Lazily builds and caches an archetype-matched agent for the opponent seat.
    `our_deck` / `our_policy_factory` (a make_agent-style callable) is the fallback
    used when the archetype is unknown or unmatched.

    Also exposes the archetype's EXACT known 60-card decklist (`self.deck`) when
    detected -- every archetype this module recognizes has one on disk (the same
    file each loader itself reads to build its pilot, or anti_crustle's/
    grimmsnarl's JSON deck). Callers (beam2_policy.det()) use this for a proper
    exclusion-based hidden-info sampler instead of guessing from seen cards
    alone: sampling WITH replacement from "cards we've happened to see" can
    imagine duplicate/impossible cards (e.g. a 3rd copy of a 1-of), which looks
    like a devastating combo the opponent doesn't actually have and drives
    phantom worst-case search results (see exp038/SESSION_NOTES.md)."""

    def __init__(self, our_deck, our_policy_factory):
        self._our_deck = our_deck
        self._our_policy_factory = our_policy_factory
        self._archetype = None
        self._agent = None
        self.deck = None  # exact 60-card decklist for the detected archetype, or None

    def _build(self, archetype):
        try:
            if archetype == "Dragapult ex":
                import load_dragapult as LD
                return LD.make_dragapult_agent(), _read_deck_csv(_DRAGAPULT_DECK_CSV)
            if archetype == "Archaludon ex":
                from load_archaludon import make_archaludon_agent
                return make_archaludon_agent(), _read_deck_csv(_ARCHALUDON_DECK_CSV)
            if archetype == "Great Tusk LO (mill)":
                from load_lo import make_lo_agent
                return make_lo_agent(), _read_deck_csv(_LO_DECK_CSV)
            if archetype == "Crustle":
                import anti_crustle as AC
                return AC.make_crustle_agent(), list(AC.CRUSTLE_DECK)
            if archetype == "Mega Lucario ex + Solrock/Lunatone":
                import anti_crustle as AC
                return AC.make_agent(AC.LUCARIO_DECK), list(AC.LUCARIO_DECK)
            if archetype == "Marnie's Grimmsnarl ex":
                grim = json.load(open(_GRIMMSNARL_DECK_JSON))
                return self._our_policy_factory(grim), list(grim)
        except Exception:
            pass
        return None, None

    def policy(self, obs):
        """Return a callable(obs_dict) -> action for the opponent's seat, given
        the CURRENT observation (used to detect/refresh their archetype)."""
        my = obs.current.yourIndex
        opp = obs.current.players[1 - my]
        archetype = classify(visible_ids(opp))
        if archetype != self._archetype or self._agent is None:
            agent, deck = self._build(archetype)
            if agent is not None:
                self._archetype = archetype
                self._agent = agent
                self.deck = deck
            elif self._agent is None:
                self._archetype = "__fallback__"
                self._agent = self._our_policy_factory(self._our_deck)
                self.deck = None
        return self._agent
