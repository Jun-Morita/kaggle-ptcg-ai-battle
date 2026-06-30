"""exp025 — un-KOable-active redirect rule (axis 3: opponent-situational play).

Real-PTCG principle: don't keep hitting into a wall you can't break; deny the developing
bench instead. vs a tank (Archaludon ex HP300+, our max hit ~140) our plan can only chip
the un-KOable active. Rule: when the opponent ACTIVE is un-KOable this turn, (a) penalize
targeting it, (b) bonus the LOWEST-HP benched threat (deny the next attacker, e.g. Duraludon
130 before it evolves) — gust pulls it with Boss. Built on revenge (v011). Env REVENGE_BONUS.
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

# un-KOable threshold: our realistic max single hit (~140 Snorlax / 130 windowed Revenge)
_UNKO = '''
_UNKO_HP = 200   # opponent active above this is un-KOable by us this turn

def _unko_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    t = self.state.turn
    cur_opp = len(self.opponent.prize)
    if t != _rev["turn"]:
        _rev["window"] = (_rev["last_opp"] is not None and cur_opp < _rev["last_opp"])
        _rev["last_opp"] = cur_opp
        _rev["turn"] = t
    window = _rev["window"]
    # is the opponent ACTIVE un-KOable this turn?  (high HP, and we have no KO line on it)
    opp_active = (self._opponent_board()[0] if self._opponent_board() else None)
    active_unkoable = opp_active is not None and opp_active.hp >= _UNKO_HP
    # lowest-HP benched opponent threat (deny the developing attacker)
    bench_hps = [(op.hp, ti) for ti, op in enumerate(self._opponent_board()) if op is not None and ti >= 1]
    min_bench_ti = min(bench_hps)[1] if bench_hps else -1
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
                    sc += 500 + __PRIZE_W__ * (prize - 1)
                # ===== exp025 un-KOable redirect =====
                if active_unkoable and prize == 0:
                    if ti == 0:
                        sc -= 400                     # stop chipping the wall
                    elif ti == min_bench_ti:
                        sc += 250                     # deny the lowest-HP developing threat
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _unko_plan_attack
'''
_UNKO = (_UNKO.replace("__REVENGE_BONUS__", str(RV.REVENGE_BONUS))
              .replace("__PRIZE_W__", str(RV.PRIZE_W)))

PATCH_SRC = RV.PATCH_SRC + "\n" + _UNKO
_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"unko_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
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
