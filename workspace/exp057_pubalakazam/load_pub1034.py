"""exp057 -- load the public 1034.6-Elo search-augmented Alakazam agent.

Source (attribution): Kaggle notebook tientrum/search-augmented-heuristic-agent-alakazam
(public checkpoint, converged 1034.6 on the live ladder, scored 2026-07-05).
Safety-reviewed 2026-07-15: imports os/json/cg.api only; eval( hits are the
_leaf_eval function; open() reads deck.csv / optional alak_w.json; no network,
no subprocess, no dynamic exec.
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
from harness import load_engine  # noqa: E402

AGENT_DIR = os.path.join(HERE, "agent")
_n = [0]


def pub1034_deck():
    return json.load(open(os.path.join(HERE, "pub1034_deck.json")))


def make_pub1034_agent(deck=None):
    load_engine()
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pub1034_{_n[0]}", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    d = list(deck) if deck else pub1034_deck()

    def agent(obs):
        if obs.get("select") is None:
            return list(d)
        return mod.agent(obs)
    return agent
