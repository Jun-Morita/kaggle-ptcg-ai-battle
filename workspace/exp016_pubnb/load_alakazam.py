"""Load the public 5th-place rule-based Alakazam agent as an opponent.

Source (public Kaggle notebook, attribution): rule-based-not-psychic-alakazam-best-5th.
We add this strong, top-meta archetype (Alakazam "Powerful Hand" = 20 x hand size)
to our local evaluation pool — we identified Alakazam as a top archetype (THIRD PTCG
#2/#3) but lacked an Alakazam opponent. The 3rd-party code lives under
references/raw/ (gitignored); this loader is ours.
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa: E402

ALAKAZAM_DIR = os.path.join(ROOT, "references", "raw", "public_notebooks", "alakazam")
_n = [0]


def make_alakazam_agent():
    """Return the public Alakazam agent (reads its own deck.csv)."""
    load_engine()  # cg must be importable before main.py's `from cg.api import ...`
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"alakazam_{_n[0]}", os.path.join(ALAKAZAM_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(ALAKAZAM_DIR)  # main.py reads "deck.csv" from cwd
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def alakazam_deck():
    with open(os.path.join(ALAKAZAM_DIR, "deck.csv")) as f:
        return [int(x) for x in f.read().split() if x.strip()]
