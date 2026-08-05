"""Load the public 911.3 Grimmsnarl agent as a LOCAL opponent / reference pilot.

Source: public Kaggle notebook tetsutani/grimmsnarl-ex-damage-transfer-control
(75 votes, current ladder score 911.3 as of 2026-08-04). The notebook embeds its
agent as a base64 tar; ref_tetsutani/ is that tar extracted, kept gitignored and
never redistributed.

Why it is worth the trouble:
  - Its deck.csv is IDENTICAL to ours (60/60 cards, exact multiset). The entire
    66-point gap to our 845 is piloting, not construction.
  - It is the first opponent we have that is STRONGER than us. Every local gate so
    far saturated (we beat the rule-based field 0.89-0.99 while scoring 0.55 on the
    ladder), and the learned Alakazam pilot ranked v15s ABOVE v3s, backwards from
    the ladder. A stronger reference at least cannot saturate.
  - Its architecture is a council: six hand-written policy generations vote, and a
    fitted per-SelectContext coalition table breaks ties. Nothing is imitated from
    top-player replays.

Used for analysis and as a sparring opponent ONLY. Any idea taken from it gets
reimplemented on our side; its code and weights never enter our submission.
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF_DIR = os.path.join(HERE, "ref_tetsutani")
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa: E402

DECK = [int(x) for x in open(os.path.join(REF_DIR, "deck.csv")).read().split()
        if x.strip().isdigit()]
_n = [0]


def make_ref_agent():
    """Fresh instance per game: the council keeps cross-turn ledgers and resets
    them when it sees an observation with select=None (start of game)."""
    load_engine()
    _n[0] += 1
    prev_cwd = os.getcwd()
    # REF_DIR must STAY on sys.path: their main.py imports policy_core lazily, on
    # the first real decision, not at module exec. Restoring sys.path after the
    # exec (the obvious thing, and what this did first) made every later import
    # fail -- and their agent() swallows the ImportError and returns
    # list(range(minCount)), a legal but arbitrary move. It played that way on 115
    # of 196 decisions and lost 3-117, which read as us being far stronger.
    if REF_DIR not in sys.path:
        sys.path.insert(0, REF_DIR)
    os.chdir(REF_DIR)
    try:
        spec = importlib.util.spec_from_file_location(
            f"ref_main_{_n[0]}", os.path.join(REF_DIR, "main.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod._load_policy()          # force the lazy import now, while cwd is right
    finally:
        os.chdir(prev_cwd)

    def agent(obs_dict):
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        if sel is None:
            return list(DECK)
        return mod.agent(obs_dict)

    agent._mod = mod
    return agent
