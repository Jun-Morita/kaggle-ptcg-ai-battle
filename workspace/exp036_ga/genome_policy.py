"""exp036 — genome-parameterized pilot: the v012 chain (router→discipline→gust→
revenge) with its core scoring constants scaled by a log2-multiplier genome.

Genome (12 genes, each log2-multiplier in [-2, 2]; ALL-ZERO == exact v012 pilot):
  0 g_prize    target_score: prize_count * 1000
  1 g_ene      target_score: energies * 150
  2 g_tool     target_score: tools * 100
  3 g_stage2   target_score: stage2 +250
  4 g_stage1   target_score: stage1 +130
  5 g_hp       target_score: +hp weight
  6 g_atk_act  plan: active-attacker bonus 220
  7 g_tgt_act  plan: active-target bonus 300
  8 g_prizeKO  plan: prize-KO bonus 500 (+ PRIZE_W term untouched)
  9 g_revenge  plan: REVENGE_BONUS (base 50)
 10 g_chip     plan: chip score weight (damage/hp fraction), default 1.0
 11 g_trevcap  discipline: _MAX_TREV_LINE = round(3 * 2**g), clamped [2, 5]

make_agent(deck, genome) builds a fresh module (same mechanism as
revenge_policy.make_agent) and execs a genome override patch last.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp018_adaptive"),
           os.path.join(_ROOT, "workspace", "exp022_megastarmie"),
           os.path.join(_ROOT, "workspace", "exp023_revenge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import revenge_policy as RV

N_GENES = 12
GENE_NAMES = ["g_prize", "g_ene", "g_tool", "g_stage2", "g_stage1", "g_hp",
              "g_atk_act", "g_tgt_act", "g_prizeKO", "g_revenge", "g_chip", "g_trevcap"]

# genome override: redefines target_score + _plan_attack with scaled constants.
# Template mirrors revenge_policy._REVENGE exactly (identity when all mults = 1).
_GENOME = '''
# ===== exp036 genome override (scaled constants; mults==1 -> identical to v012) =====
_gm_orig_target_score = target_score
def target_score(pokemon):
    data = card_table[pokemon.id]
    score = prize_count(pokemon) * (1000.0 * __M_PRIZE__)
    score += len(pokemon.energies) * (150.0 * __M_ENE__)
    score += len(pokemon.tools) * (100.0 * __M_TOOL__)
    if data.stage2:
        score += 250.0 * __M_STAGE2__
    elif data.stage1:
        score += 130.0 * __M_STAGE1__
    if pokemon.id in {144, 322, 323, 337}:
        score -= 200
    if pokemon.id == 112 and len(pokemon.energies) >= 1:
        score += 300
    score += pokemon.hp * __M_HP__
    return score

def _gm_plan_attack(self):
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
                dmg += __REVENGE__
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
                    sc *= (d / op.hp) * __M_CHIP__
                if len(self.opponent.prize) <= prize:
                    sc = 50000
                sc += bscore + ((220.0 * __M_ATK_ACT__) if ai == 0 else 0)
                sc += (300.0 * __M_TGT_ACT__) if ti == 0 else 0
                sc += ecount
                if prize >= 1:
                    sc += 500.0 * __M_PRIZEKO__
                if sc > best:
                    best = sc
                    plan = AttackPlan(attacker=ai, target=ti, attack_index=idx,
                                      remain_hp=op.hp - d, needs_energy=needs_e)
LucarioPolicy._plan_attack = _gm_plan_attack
_MAX_TREV_LINE = __TREVCAP__
'''


def genome_patch(genome):
    assert len(genome) == N_GENES
    m = [2.0 ** float(g) for g in genome]
    rb = RV.REVENGE_BONUS if RV.REVENGE_BONUS else 50
    trevcap = max(2, min(5, round(3 * m[11])))
    src = (_GENOME
           .replace("__M_PRIZE__", repr(m[0])).replace("__M_ENE__", repr(m[1]))
           .replace("__M_TOOL__", repr(m[2])).replace("__M_STAGE2__", repr(m[3]))
           .replace("__M_STAGE1__", repr(m[4])).replace("__M_HP__", repr(m[5]))
           .replace("__M_ATK_ACT__", repr(m[6])).replace("__M_TGT_ACT__", repr(m[7]))
           .replace("__M_PRIZEKO__", repr(m[8])).replace("__REVENGE__", repr(rb * m[9]))
           .replace("__M_CHIP__", repr(m[10])).replace("__TREVCAP__", repr(trevcap)))
    return src


def patch_src(genome):
    return RV.PATCH_SRC + "\n" + genome_patch(genome)


_n = [0]


def make_agent(deck, genome):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"ga_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(patch_src(genome), mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
