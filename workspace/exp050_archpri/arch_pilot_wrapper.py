"""exp050 -- make_agent(deck) wrapper around the public Archaludon pilot so it
can be fed to exp048's policy_diff_fixed.py (which expects make_agent(deck))."""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp025_unkoable"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))

from load_archaludon import make_archaludon_agent  # noqa: E402


def make_agent(deck):
    # the public pilot reads its own deck.csv; the deck arg only matters for the
    # deck-submission pseudo-step, which policy_diff never exercises
    return make_archaludon_agent()
