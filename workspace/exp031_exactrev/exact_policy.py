"""exp031 — EXACT revenge window from engine source (references/knowledge/engine_source_0703.md).

Engine truth (SatisfyCondition.h): Horrifying Revenge +100 requires
turnHistories[1].koAttackDamageHop = a HOP'S Pokemon KO'd by attack damage on the
opponent's last turn. v011's proxy (opponent took a prize) false-fires when a
non-Hop's Pokemon (Dunsparce 305 / Dudunsparce 66) is KO'd — which is why the sweep
preferred a hedged RB=50 over the true +100.

Exact detection from obs: window = (opp prize count dropped since our last turn)
AND (count of Hop's-Pokemon cards in OUR discard increased). A KO sends the Pokemon
+ its pre-evolutions to the discard, so a Hop's KO always bumps the count; a
Dudunsparce KO doesn't. With the window exact, RB can approach the true 100.

Env: REVENGE_BONUS (default 100). PATCH_SRC for build.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp022_megastarmie")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import gust_policy as G

REVENGE_BONUS = int(os.environ.get("REVENGE_BONUS", "100"))

# All Hop's Pokemon ids (engine CardImpl.h .hop() marks); ours are 878/879/304.
_EXACT = '''
_HOP_IDS = (288, 289, 298, 299, 304, 307, 308, 309, 310, 311, 878, 879)
_rev = {"turn": -2, "last_opp": None, "last_hop_dis": None, "window": False}

def _rev_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    # EXACT revenge window (engine: koAttackDamageHop): opponent took a prize AND
    # a Hop's Pokemon of ours hit the discard since our last turn.
    t = self.state.turn
    cur_opp = len(self.opponent.prize)
    hop_dis = sum(self.discard_counts[i] for i in _HOP_IDS)
    if t != _rev["turn"]:
        _rev["window"] = (_rev["last_opp"] is not None and cur_opp < _rev["last_opp"]
                          and _rev["last_hop_dis"] is not None and hop_dis > _rev["last_hop_dis"])
        _rev["last_opp"] = cur_opp
        _rev["last_hop_dis"] = hop_dis
        _rev["turn"] = t
    window = _rev["window"]
    have_e = sum(self.hand_counts[e] for e in _NONEX_ENERGY) >= 1
    for ai, me in enumerate(self._my_board()):
        if me is None:
            continue
        if ai != 0 and not self.can_switch:
            break
        atk_type = EnergyType.PSYCHIC if me.id in (_TREVENANT, _PHANTUMP) else EnergyType.COLORLESS
        for idx in range(2):
            at = self._base_attack_after_evolution(me, ai, idx)
            if at is None:
                continue
            need, dmg, bscore = at
            if me.id == _TREVENANT and idx == 0 and window:
                dmg += __REVENGE_BONUS__
            ecount = len(me.energies)
            needs_e = False
            if ecount < need:
                if have_e and not self.state.energyAttached:
                    ecount += 1
                    needs_e = ecount >= need
                if not needs_e:
                    continue
            for ti, op in enumerate(self._opponent_board()):
                if op is None:
                    continue
                if ti != 0 and not self.can_gust:
                    break
                d = dmg
                od = card_table[op.id]
                if atk_type != EnergyType.COLORLESS and od.weakness == atk_type:
                    d *= 2
                elif atk_type != EnergyType.COLORLESS and od.resistance == atk_type:
                    d = max(0, d - 30)
                sc = target_score(op)
                prize = prize_count(op) if op.hp <= d else 0
                if prize == 0:
                    sc *= d / op.hp
                if len(self.opponent.prize) <= prize:
                    sc = 50000
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                if prize >= 1:
                    sc += 500
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _rev_plan_attack
'''

_EXACT = _EXACT.replace("__REVENGE_BONUS__", str(REVENGE_BONUS))

PATCH_SRC = G.PATCH_SRC + "\n" + _EXACT

_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"exactrev_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
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
