"""exp024 — TR-engine fetch prototype: phase-aware _score_to_hand on the revenge base.

The TR deck has NO draw-Pokemon engine; card advantage comes entirely from tutors
(Transceiver->Petrel->any Trainer, Hilda, Lillie). Our _TO_HAND_PRI leaves the draw/
chain trainers (Lillie/Pokegear/Xerosic/PokePad) at default 100, so a Petrel always
grabs Choice Band(200)/Boss(175) — tools/disruption — over the draw+chain that the
engine needs early. Fix: EARLY (our prizes>=4 or no evolved Trevenant yet) boost
draw/chain/setup fetches; keep Boss/Choice Band high LATE. Env REVENGE_BONUS honored.
"""
from __future__ import annotations
import importlib.util, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in ("exp001_harness", "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge"):
    pp = os.path.join(_ROOT, "workspace", _p)
    if pp not in sys.path:
        sys.path.insert(0, pp)
os.environ.setdefault("REVENGE_BONUS", "50")
import revenge_policy as RV

_TR = '''
# ===== exp024 TR-engine phase-aware fetch priority =====
_TR_EARLY = {1227: 215, 1134: 205, 1225: 200, 1122: 175, 1219: 170, 1152: 150, 1115: 165}
_orig_sth_tr = LucarioPolicy._score_to_hand
def _tr_score_to_hand(self, card):
    base = _orig_sth_tr(self, card)
    early = len(self.me.prize) >= 4 or self.field_counts[879] == 0
    if early and card.id in _TR_EARLY:
        return _TR_EARLY[card.id] - self.hand_counts[card.id] * 60
    return base
LucarioPolicy._score_to_hand = _tr_score_to_hand
'''

PATCH_SRC = RV.PATCH_SRC + "\n" + _TR
_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"tr_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)
    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
