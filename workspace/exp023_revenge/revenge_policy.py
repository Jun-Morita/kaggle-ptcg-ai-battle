"""exp023 — real-strategy-informed piloting on the v010 gust base.

Three REAL Pokémon-TCG principles encoded as tunable constants (1-D swept by sweep.py):

1. REVENGE WINDOW (the deck's defining mechanic). Hop's Trevenant "Horrifying Revenge"
   is 1 energy / 30, but **+100 (=130) if a Hop's Pokémon was KO'd by an attack on the
   opponent's last turn**. router_policy hard-codes it as a flat 30, so the pilot never
   sees the 130 revenge-KO and mis-targets. We detect the window (opponent took a prize
   since our last turn => we lost a Pokémon) and add REVENGE_BONUS to Trevenant's Revenge
   damage during planning, so the policy recognizes the revenge KO and targets/evolves
   to cash it. (The engine applies the real +100 regardless; this only fixes the CHOICE.)

2. PRIZE TRADE. Single-prize decks win by KOing multi-prize ex. The gust fix gave a flat
   +500 for any prize KO; we add PRIZE_W * (target_prize - 1) so KOing a 2-3 prize ex is
   valued above KOing a 1-prize basic (hunt the ex).

3. BACKUP CHARGE (continuity). Once the active is armed, divert energy to a benched
   Trevenant/Phantump so we can revenge-KO the turn after a trade instead of wasting it.

Constants come from env (REVENGE_BONUS / PRIZE_W / BACKUP_CHARGE); defaults reproduce
v010 exactly (REVENGE_BONUS=0, PRIZE_W=0, BACKUP_CHARGE=0). PATCH_SRC consumed by
build_submission.py for the final crash-safe artifact.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp001_harness"),
           os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp018_adaptive"),
           os.path.join(_ROOT, "workspace", "exp022_megastarmie")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import gust_policy as G

REVENGE_BONUS = int(os.environ.get("REVENGE_BONUS", "0"))
PRIZE_W = int(os.environ.get("PRIZE_W", "0"))
BACKUP_CHARGE = int(os.environ.get("BACKUP_CHARGE", "0"))

# _plan_attack: gust logic + revenge-window damage + prize-trade-weighted KO bonus.
_REVENGE = '''
_rev = {"turn": -2, "last_opp": None, "window": False}

def _rev_plan_attack(self):
    global plan
    best = -1
    plan = AttackPlan()
    if self.state.turn < 2:
        return
    # revenge window: opponent took a prize since our last turn => a Hop's Pokemon was KO'd
    t = self.state.turn
    cur_opp = len(self.opponent.prize)
    if t != _rev["turn"]:
        _rev["window"] = (_rev["last_opp"] is not None and cur_opp < _rev["last_opp"])
        _rev["last_opp"] = cur_opp
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
            # (1) revenge window: Trevenant's Horrifying Revenge does +100 (model as +BONUS)
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
                # (2) prize trade: flat +500 for a KO, plus extra for multi-prize (ex) targets
                if prize >= 1:
                    sc += 500 + __PRIZE_W__ * (prize - 1)
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _rev_plan_attack

# (3) backup charge: when the active is armed, charge a benched non-ex attacker for continuity
if __BACKUP_CHARGE__:
    _orig_ets_bc = LucarioPolicy._energy_target_score
    def _bc_energy_target_score(self, pokemon, active):
        if not active and pokemon.id in (_TREVENANT, _PHANTUMP) and len(pokemon.energies) == 0:
            board = self._my_board()
            act = board[0] if board else None
            if act is not None and len(act.energies) >= 1:
                return 40
        return _orig_ets_bc(self, pokemon, active)
    LucarioPolicy._energy_target_score = _bc_energy_target_score
'''

_REVENGE = (_REVENGE
            .replace("__REVENGE_BONUS__", str(REVENGE_BONUS))
            .replace("__PRIZE_W__", str(PRIZE_W))
            .replace("__BACKUP_CHARGE__", str(BACKUP_CHARGE)))

PATCH_SRC = G.PATCH_SRC + "\n" + _REVENGE

_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"revenge_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
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
    agent._mod = mod  # non-invasive: lets callers snapshot/restore cross-turn
                       # globals (e.g. _rev) when reusing this instance for
                       # hypothetical search rollouts spanning turn boundaries
    return agent
