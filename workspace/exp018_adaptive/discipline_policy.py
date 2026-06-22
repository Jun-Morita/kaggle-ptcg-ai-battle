"""v008 router + prize-liability DISCIPLINE patch (exp018).

Evidence (exp018 analyze_adaptation): top non-ex players win the mirror (Debauchery
0.64 vs our 0.38) NOT by reading the opponent but by consistent DISCIPLINE — they
bench FEWER (~3) than us (~4+), minimizing prizes given up, and they conserve
resources. The base policy's `_score_play_pokemon` returns 20000 for EVERY non-ex
Pokemon (it only throttles Lucario cards) -> we over-deploy. This patch adds
real-PTCG decision indicators as triggers:
  - BENCH / PRIZE-LIABILITY: cap the Trevenant attacker line (~3), keep an open
    bench slot, don't flood Phantump, 1 Snorlax/Cramorant is plenty.
  - ENERGY: don't waste energy on an already-armed 1-energy attacker.
  - PRIZE STATE: when behind on prizes, allow one more attacker (need offense).
Everything else identical to v008 (router). Tunable via the constants below.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp001_harness"),
           os.path.join(_ROOT, "workspace", "exp013_router")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import router_policy as R

# how many Trevenant-line attackers we want before throttling further bench
_MAX_TREV_LINE = 3
_KEEP_OPEN_SLOT = True

_DISCIPLINE = '''
# ===== exp018 prize-liability discipline (non-ex only) =====
_MAX_TREV_LINE = %d
_KEEP_OPEN_SLOT = %s

def _bench_free(self):
    return self.me.benchMax - len(self.me.bench)

_CRUSTLE, _DWEBBLE = 345, 344
def _opp_is_wall(self):
    # vs a stall wall (Crustle/Dwebble) we must DEVELOP, not ration the bench
    return any(p is not None and p.id in (_CRUSTLE, _DWEBBLE) for p in self._opponent_board())

_orig_spp = LucarioPolicy._score_play_pokemon
def _disc_score_play_pokemon(self, card):
    if not _DECK_NONEX or _opp_is_wall(self):
        return _orig_spp(self, card)
    cid = card.id
    free = _bench_free(self)
    line = self.field_counts[_TREVENANT] + self.field_counts[_PHANTUMP]
    behind = len(self.me.prize) > len(self.opponent.prize)   # we have MORE prizes left = behind
    base = 20000
    if cid == _PHANTUMP:
        # evolve fuel for Trevenant: want a few, not a flood (each is a 1-prize KO target)
        cap = _MAX_TREV_LINE + (1 if behind else 0)
        if line >= cap:
            return -1
        s = base + (300 if line == 0 else 120 if line == 1 else 40)
        if _KEEP_OPEN_SLOT and free <= 1 and line >= 2:
            s -= 6000                      # keep a slot; we already have attackers
        return s
    if cid == _SNORLAX:                    # 1 benched Snorlax powers Extra Helpings; more = liability
        return -1 if self.field_counts[_SNORLAX] >= 1 else base + 60
    if cid == _CRAMORANT:                  # situational attacker; one is enough
        return -1 if self.field_counts[_CRAMORANT] >= 1 else base + 20
    if cid in (_DUNSPARCE, _DUDUNSPARCE):  # draw engine: want ~1 line, not stacks
        if self.field_counts[_DUNSPARCE] + self.field_counts[_DUDUNSPARCE] >= 2:
            return -1
        return base + 80
    if _KEEP_OPEN_SLOT and free <= 1:      # any other basic: don't fill the last slot
        return base - 4000
    return base
LucarioPolicy._score_play_pokemon = _disc_score_play_pokemon

_ONE_ENERGY = {_TREVENANT, _PHANTUMP, _CRAMORANT}
_orig_ets = LucarioPolicy._energy_target_score
def _disc_energy_target_score(self, pokemon, active):
    if _DECK_NONEX and pokemon.id in _ONE_ENERGY and len(pokemon.energies) >= 2:
        return -1                          # 1-energy attacker already armed -> don't waste energy
    return _orig_ets(self, pokemon, active)
LucarioPolicy._energy_target_score = _disc_energy_target_score
''' % (_MAX_TREV_LINE, _KEEP_OPEN_SLOT)

PATCH_SRC = R.PATCH_SRC + "\n" + _DISCIPLINE

_n = [0]


def make_agent(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"disc_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
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
