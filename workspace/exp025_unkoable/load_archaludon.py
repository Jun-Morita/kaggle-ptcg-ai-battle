"""Load the public Archaludon ex / Cinderace agent (reviewed-safe 3rd-party code).

Source: public Kaggle notebook 'a-sample-archaludon-75-wr-vs-my-1300-starmie'.
Now the LB-apex archetype (ShumpeiNomura #1 1465, Takaaki Matsuda #2 1349 run Metal).
main.py reviewed: pure rule-based (os/random/sys/cg.api only, reads deck.csv). Metal
Defender 220 OHKOs our non-ex; Archaludon ex HP300 (un-KOable by us) = the new matchup.
"""
from __future__ import annotations
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa

ARCH_DIR = os.path.join(HERE, "archaludon_opp")
_n = [0]


def make_archaludon_agent():
    load_engine()
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"archaludon_{_n[0]}", os.path.join(ARCH_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(ARCH_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    deck = [int(x) for x in open(os.path.join(ARCH_DIR, "deck.csv")).read().split() if x.strip().isdigit()]

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        if o.select is None:
            return list(deck)
        return mod.agent(obs_dict)
    agent._mod = mod  # non-invasive: lets callers snapshot/restore this pilot's
                       # cross-turn globals (_cur_turn_logs etc.) when reused for
                       # hypothetical search rollouts
    return agent
