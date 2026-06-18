"""Produce an anti-Crustle patched lucario_v2 policy source.

Single surgical change to _plan_attack: an ex/megaEx attacker deals 0 to an
ex-immune target (Crustle's Safeguard). This makes the existing attack-planning
machinery avoid wasting turns attacking Crustle with Mega Lucario ex and instead
pick the non-ex Hariyama line (Wild Press 210 one-shots Crustle's 150 HP).
Returns the patched source string.
"""
from __future__ import annotations

import os

POLICY_SRC = os.path.join(os.path.dirname(__file__), "..", "exp002_baselines", "policies", "lucario_v2.py")

HELPER = '''
# exp007 anti-Crustle: cards whose ability prevents damage from opponent's ex.
def _ex_immune_card(card_id):
    c = card_table.get(card_id)
    if c is None:
        return False
    for s in c.skills:
        t = (s.text or "")
        if "by attacks from your opponent" in t and "{ex}" in t and "Prevent all damage" in t:
            return True
    return False
'''

OLD = """                    damage = base_damage
                    op_data = card_table[op_pokemon.id]
                    if op_data.weakness == EnergyType.FIGHTING:
                        damage *= 2
                    elif op_data.resistance == EnergyType.FIGHTING:
                        damage -= 30
"""

NEW = """                    damage = base_damage
                    op_data = card_table[op_pokemon.id]
                    if op_data.weakness == EnergyType.FIGHTING:
                        damage *= 2
                    elif op_data.resistance == EnergyType.FIGHTING:
                        damage -= 30
                    # exp007 anti-Crustle: ex/megaEx attacks deal 0 to ex-immune targets.
                    _my_d = card_table[my_pokemon.id]
                    if (_my_d.ex or _my_d.megaEx) and _ex_immune_card(op_pokemon.id):
                        damage = 0
"""


def patched_source() -> str:
    src = open(POLICY_SRC).read()
    assert OLD in src, "damage block not found (policy changed?)"
    src = src.replace(OLD, NEW, 1)
    # inject helper right after card_table definition
    anchor = "card_table = {card.cardId: card for card in all_card}\n"
    assert anchor in src
    src = src.replace(anchor, anchor + HELPER, 1)
    return src


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "policy_anticrustle.py")
    open(out, "w").write(patched_source())
    print("wrote", out)
