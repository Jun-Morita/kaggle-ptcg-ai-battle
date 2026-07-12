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
import random
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


def _random_agent(obs_dict):
    """Uniform-random legal move -- same logic as train_mcts.random_agent,
    duplicated (not imported) to avoid a circular import (train_mcts imports
    this module at load time). Added 2026-07-06 (user request): a curriculum
    "easy tier" opponent the trainee can reliably beat, mixed into the pool
    alongside the competent rule-based teachers -- Stage 2/4 only ever saw
    winnable games via mirror_revenge (also non-trivial) or hard 4 real decks;
    there was no guaranteed source of early positive-outcome trajectories."""
    from cg.api import to_observation_class
    obs = to_observation_class(obs_dict)
    return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)


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
        # curriculum easy tier (2026-07-06): reliably winnable so the trainee
        # accumulates some positive-outcome trajectories early, not just
        # losses against competent teachers. Weighted low -- a supplement,
        # not the bulk of training (mirror_revenge/hard-4 stay dominant).
        ("random", list(trainee_deck), lambda deck: _random_agent, 0.5),
        # grimmsnarl (2026-07-10): the new ladder #1 deck (Yushin Ito switched
        # to the exp028 "Debauchery" Marnie's Grimmsnarl ex rush and jumped
        # #7->#1; it beats our archetype 0.71 at n=251 on the ladder). Piloted
        # by our generic revenge policy, same convention as exp028's eval.
        ("grimmsnarl",
         json.load(open(os.path.join(ROOT, "workspace", "exp028_debauchery", "grimmsnarl_deck.json"))),
         lambda deck: RVP.make_agent(deck), 1.0),
    ]
