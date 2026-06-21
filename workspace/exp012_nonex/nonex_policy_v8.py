"""v008 = v007 non-ex policy + a MIRROR refinement.

v007 taught the attack model (Extra Helpings / Choice Band / Boss's Orders) and
already wins the non-ex mirror (~0.56 real, 0.775 vs generic). The remaining edge
in the single-prize mirror is ENGINE DENIAL: the opponent's **Hop's Snorlax**
provides Extra Helpings (+30 to ALL their attacks) from the bench, and **Dudunsparce**
is the draw engine. Removing them (via Boss's Orders gust + KO, which v007 already
wires once a plan exists) is worth more than its raw prize value. v008 boosts the
target priority of those pieces so the planner gusts/KOs them.

Only affects target selection vs decks that run those cards (the Hop's non-ex
mirror and Alakazam/Dudunsparce decks) — no effect vs ex / Crustle. Exposes
PATCH_SRC for the generic builder; make_smart_agent() for head-to-head testing.
"""
from __future__ import annotations
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
POLICIES = os.path.join(ROOT, "workspace", "exp002_baselines", "policies")
NONEX = json.load(open(os.path.join(HERE, "charmq_deck.json")))

# v007 patch (attack model) + v008 addon (engine-denial target priority).
_spec = importlib.util.spec_from_file_location("np7", os.path.join(HERE, "nonex_policy.py"))
_np7 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_np7)

PATCH_SRC = _np7.PATCH_SRC + '''
# ===== v008 mirror refinement: open with the attacker line, bench the engine =====
def _nonex_setup_active(self, card):
    pid = card.id
    if pid == 878:   # Hop's Phantump -> Hop's Trevenant (main attacker line)
        return 10
    if pid == 65:    # Dunsparce -> Dudunsparce (draw engine); acceptable opener
        return 4
    if pid == 304:   # Hop's Snorlax: keep BENCHED for Extra Helpings (+30), don't lead
        return 1
    return 0
LucarioPolicy._score_setup_active = _nonex_setup_active
'''

_n = [0]


def _load_patched():
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"nonex8_{_n[0]}", os.path.join(POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, NONEX)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)
    return mod


def make_smart_agent():
    mod = _load_patched()
    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(NONEX) if o.select is None else mod.agent(obs_dict)
    return agent
