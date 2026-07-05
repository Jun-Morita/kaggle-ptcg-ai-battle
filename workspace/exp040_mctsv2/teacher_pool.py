"""Stage 2 teacher pool: diverse (deck, pilot) matchups for selfplay_vs_teacher_pool
(train_mcts.py), per user request 2026-07-05 -- deck diversity + reusing past
submitted/3rd-party AIs as sparring partners, not just a single mirror opponent.

Spans exactly our established 5-matchup evaluation field (crustle/dragapult/
archaludon/ex_lucario/mirror -- the same field used by exp035-039's run_*.sh
chunked evals), so self-play exposure matches what we actually measure against.
Deck paths / agent constructors reused from exp038's opponent_model.py mapping
(same underlying files, no need to re-derive them).
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp007_anti_crustle"),
          os.path.join(ROOT, "workspace", "exp020_deckinnov"),
          os.path.join(ROOT, "workspace", "exp025_unkoable"),
          os.path.join(ROOT, "workspace", "exp023_revenge"),
          os.path.join(ROOT, "workspace", "exp035_turnbeam")):
    if p not in sys.path:
        sys.path.insert(0, p)

_DRAGAPULT_DECK_CSV = os.path.join(ROOT, "references", "raw", "public_notebooks", "dragapult", "deck.csv")
_ARCHALUDON_DECK_CSV = os.path.join(ROOT, "workspace", "exp025_unkoable", "archaludon_opp", "deck.csv")


def _read_deck_csv(path):
    return [int(x) for x in open(path).read().split() if x.strip().isdigit()]


def build_teacher_pool(trainee_deck):
    """Returns list of (name, deck, factory(deck)->agent, weight). `factory`
    always takes a `deck` arg for a uniform call signature even though the
    3rd-party pilots (dragapult/archaludon) ignore it and read their own fixed
    decklist internally -- they only ever pilot that exact deck."""
    import anti_crustle as AC
    import revenge_policy as RVP
    import turnbeam_policy as TB
    from load_dragapult import make_dragapult_agent
    from load_archaludon import make_archaludon_agent

    return [
        ("crustle", list(AC.CRUSTLE_DECK), lambda deck: AC.make_crustle_agent(), 1.0),
        ("ex_lucario", list(AC.LUCARIO_DECK), lambda deck: AC.make_agent(AC.LUCARIO_DECK), 1.0),
        ("dragapult", _read_deck_csv(_DRAGAPULT_DECK_CSV), lambda deck: make_dragapult_agent(), 1.0),
        ("archaludon", _read_deck_csv(_ARCHALUDON_DECK_CSV), lambda deck: make_archaludon_agent(), 1.0),
        # mirror: teacher plays the SAME deck as the trainee. Weighted higher
        # (cheapest: no search) with an occasional stronger v014 sparring
        # partner mixed in (turnbeam_policy has its OWN internal beam search,
        # so it's slower -- low weight keeps it "occasional", not the bulk).
        ("mirror_revenge", list(trainee_deck), lambda deck: RVP.make_agent(deck), 2.0),
        ("mirror_turnbeam", list(trainee_deck), lambda deck: TB.make_agent(deck), 0.3),
    ]
