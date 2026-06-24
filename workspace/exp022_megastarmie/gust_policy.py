"""v009 discipline + BOSS'S ORDERS gust fix (exp022) — the data-driven mirror rule.

Mogja(#3) wins the mirror (0.68) with our EXACT deck partly by using Boss's Orders
~1.6x/game to gust+KO a benched piece for a prize; OUR policy plays it 0x/game because
the non-ex plan gives the ACTIVE a +300 bias, so plan.target is ~always 0, and Boss's
Orders is scored -1 unless plan.target>=1. Fix: reward any PRIZE-taking KO (+500) so a
benched KO beats chipping an un-KO-able active -> the plan targets the bench -> Boss's
Orders gets played. Active KO still preferred over bench KO (it also keeps the +300).
Everything else = v009 (exp018 discipline). PATCH_SRC consumed by build_submission.py.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp001_harness"),
           os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp018_adaptive")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import discipline_policy as D

_GUST = '''
# ===== exp022 Boss's Orders gust fix: reward prize-taking KOs so we gust the bench =====
def _gust_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
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
                # reward TAKING A PRIZE so a benched KO beats chipping an un-KO-able active
                sc += bscore + (220 if ai == 0 else 0) + (300 if ti == 0 else 0) + ecount
                sc += 500 if prize >= 1 else 0
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _gust_plan_attack
'''

PATCH_SRC = D.PATCH_SRC + "\n" + _GUST

_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"gust_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
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
