"""exp034 — GATED anti-spread bench discipline vs Dragapult (v013 loss-driver #1).

v013 ladder decode (84 games): Dragapult ex = 12 of 40 losses (wr 0.08), and its
meta share doubled to 15%. Loss mechanism (replay decode): Phantom Dive's bench
spread farms our 60-70HP bench basics (Dunsparce/Phantump) for prizes — our pilot
benches everything (v006 lineage), feeding the snipe.

Fix = v009's prize-liability discipline, but GATED to fire ONLY when the opponent
shows the Dreepy line (119/120/121) — exp018 showed ungated discipline regresses
the Crustle matchup; gating gives the upside without the cost.

Rules when gated ON: cap Trevenant line fuel, 1 draw line, 1 Snorlax, keep an open
slot, don't flood bench with snipeable spares; stop over-charging armed 1-energy
attackers. Layered on the v011/v012 revenge chain (PATCH_SRC composition).
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp022_megastarmie"),
           os.path.join(_ROOT, "workspace", "exp023_revenge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import revenge_policy as RV

_ANTISPREAD = '''
# ===== exp034 anti-spread discipline (fires ONLY vs the Dreepy/Dragapult line) =====
_DRAG_LINE = (119, 120, 121)
_AS_MAX_TREV_LINE = 3

def _as_opp_is_drag(self):
    if any(p is not None and p.id in _DRAG_LINE for p in self._opponent_board()):
        return True
    return any(getattr(c, "id", None) in _DRAG_LINE for c in (self.opponent.discard or []))

_as_orig_spp = LucarioPolicy._score_play_pokemon
def _as_score_play_pokemon(self, card):
    if not _DECK_NONEX or not _as_opp_is_drag(self):
        return _as_orig_spp(self, card)
    cid = card.id
    free = self.me.benchMax - len(self.me.bench)
    line = self.field_counts[_TREVENANT] + self.field_counts[_PHANTUMP]
    base = 20000
    if cid == _PHANTUMP:
        if line >= _AS_MAX_TREV_LINE:
            return -1                       # each spare Phantump = a free snipe prize
        s = base + (300 if line == 0 else 120 if line == 1 else 40)
        if free <= 1 and line >= 2:
            s -= 6000
        return s
    if cid == _SNORLAX:
        return -1 if self.field_counts[_SNORLAX] >= 1 else base + 60
    if cid in (_DUNSPARCE, _DUDUNSPARCE):
        if self.field_counts[_DUNSPARCE] + self.field_counts[_DUDUNSPARCE] >= 1:
            return -1                       # ONE draw body max vs spread (60HP snipe food)
        return base + 80
    if free <= 1:
        return base - 4000
    return base
LucarioPolicy._score_play_pokemon = _as_score_play_pokemon

_AS_ONE_ENERGY = {_TREVENANT, _PHANTUMP}
_as_orig_ets = LucarioPolicy._energy_target_score
def _as_energy_target_score(self, pokemon, active):
    if _DECK_NONEX and _as_opp_is_drag(self) and pokemon.id in _AS_ONE_ENERGY and len(pokemon.energies) >= 2:
        return -1
    return _as_orig_ets(self, pokemon, active)
LucarioPolicy._energy_target_score = _as_energy_target_score
'''

PATCH_SRC = RV.PATCH_SRC + "\n" + _ANTISPREAD

_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"antispread_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
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
