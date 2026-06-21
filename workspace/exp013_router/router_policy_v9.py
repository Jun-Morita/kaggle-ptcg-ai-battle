"""v009 = v008 router policy, with the SEARCH-TARGET priority retuned from the
charmq decision-diff.

Diff finding (policy_diff.py on charmq, our-style deck): in TO_HAND searches the
top player fetches the DRAW ENGINE (Dunsparce->Dudunsparce) first to keep the deck
flowing, while our v008 under-valued it (65:120, 66:135) and grabbed attackers/Boss.
Canonical PTCG: the consistency engine is king. v009 raises the engine's search
priority near the attacker line. Everything else identical to v008 (router).
"""
from __future__ import annotations
import importlib.util
import json
import os
import re

import router_policy as R

HERE = os.path.dirname(os.path.abspath(__file__))
POLICIES = os.path.join(R.ROOT, "workspace", "exp002_baselines", "policies")

# engine (Dunsparce 65 / Dudunsparce 66) raised near the attacker line
_NEW_PRI = ("_TO_HAND_PRI = {878: 320, 65: 295, 66: 285, 879: 280, 311: 260, "
            "19: 240, 11: 220, 1171: 200, 304: 180, 1182: 175, 1225: 160, "
            "1219: 150, 1134: 145, 1115: 140}")
PATCH_SRC = re.sub(r"_TO_HAND_PRI = \{[^}]*\}", _NEW_PRI, R.PATCH_SRC)
assert "65: 295" in PATCH_SRC, "priority patch did not apply"

_n = [0]


def make_agent(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"router9_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
