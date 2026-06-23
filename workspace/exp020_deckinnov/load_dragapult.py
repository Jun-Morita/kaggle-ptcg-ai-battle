"""Load the public strong Dragapult ex agent (reviewed-safe 3rd-party code).

Source: public Kaggle notebook 'phantom-dive-or-go-home-a-dragapult-ex-deck'
(attribution). A well-piloted Phantom Dive spread + Budew lock + Crushing Hammer
agent that claims ~80% vs the single-prize field. We add it as a real opponent to
re-test exp017 (which used the weak baseline dragapult.py and wrongly dismissed it).
main.py reviewed: pure rule-based (os/sys/collections/cg.api only, reads deck.csv).
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa

DRAGAPULT_DIR = os.path.join(ROOT, "references", "raw", "public_notebooks", "dragapult")
_n = [0]


def make_dragapult_agent():
    load_engine()
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"dragapult_{_n[0]}", os.path.join(DRAGAPULT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(DRAGAPULT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent
