"""Load the public Great Tusk LO (library-out) agent (reviewed-safe 3rd-party code).

Source: public Kaggle notebook 'I have one REAR card' (score 1083.6, 2026-07-02).
main.py reviewed: pure rule-based (os/collections/cg.api only, reads deck.csv).
Great Tusk Land Collapse mill (4/turn with Explorer's Guidance) + Crustle Safeguard
wall + Neutralization Zone; explicit mill-vs-KO win-route arithmetic.
See references/knowledge/lo_mill_notebook_0702.md. User approved local run 2026-07-02.
"""
from __future__ import annotations
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa

LO_DIR = os.path.join(HERE, "lo_agent")
_n = [0]


def make_lo_agent():
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
    deck = [int(x) for x in open(os.path.join(LO_DIR, "deck.csv")).read().split() if x.strip().isdigit()]

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        if o.select is None:
            return list(deck)
        return mod.agent(obs_dict)
    return agent
