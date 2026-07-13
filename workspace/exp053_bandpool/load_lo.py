"""Load the public Great Tusk LO (library-out / mill) agent as a local opponent.

Source: public Kaggle notebook "I have one REAR card" (LB 1083.6), already
reviewed and summarized in references/knowledge/lo_mill_notebook_0702.md.
Re-reviewed 2026-07-13 before running: imports only cg.api/collections/os/
traceback; the single open() reads its own deck.csv; no network, no subprocess,
no eval/exec.

Why it matters (exp053): our cached v020 ladder replays show the band's
"crustle_control" bucket (20% share, where we score only 0.36) is dominated by
THIS deck -- Great Tusk mill + Crustle wall + Explorer's Guidance -- not by the
pure-wall proxy (AC.CRUSTLE_DECK) our local pool has been using, which matches
the real band list only 17/60. So the pool was mis-specified exactly where we
bleed the most. This module puts the REAL deck, with its REAL dedicated pilot,
into the gauntlet.
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa: E402

LO_DIR = os.path.join(HERE, "lo_opp")
_n = [0]


def lo_deck() -> list[int]:
    with open(os.path.join(LO_DIR, "deck.csv")) as f:
        return [int(x) for x in f.read().split() if x.strip().isdigit()]


def make_lo_agent(deck: list[int] | None = None):
    """Fresh module instance per call (the pilot keeps per-game module state).

    The pilot resolves its deck lazily inside agent() via a RELATIVE 'deck.csv',
    which breaks once cwd returns to the repo root, so serve the deck ourselves
    on the deck request (obs.select is None) and delegate every real decision
    to the pilot untouched -- same wrapper pattern exp049 used for the
    Archaludon pilot.

    `deck` overrides the pilot's own list (used by the exp053 deck-ratio sweep
    to run the SAME pilot on ratio variants). The pilot's card table already
    covers every card the variants use (Jumbo Ice Cream / Hero's Cape / Terrakion
    / Ultra Ball are all scored in main.py), so this is a ratio change, not a
    deck<->pilot mismatch.
    """
    load_engine()
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    d = list(deck) if deck else lo_deck()
    assert len(d) == 60, f"deck must be 60 cards, got {len(d)}"

    def agent(obs_dict):
        if obs_dict.get("select") is None:
            return list(d)
        return mod.agent(obs_dict)

    return agent
