"""exp051 -- generate the turn-beam patch for the v020 (public Archaludon)
pilot by adapting exp035's verified _TB source.

Adaptations (ONLY these -- the beam/verify logic is byte-identical):
  1. placeholder substitution (TB_K etc., TB_VALUE hard-off);
  2. the cross-turn-global snapshot/restore around planning: exp035 shields
     revenge's `_rev` dict; the Archaludon pilot's cross-turn globals are
     `_opp_last_attack_id` (scalar) and `_cur_turn_logs` (list), both mutated
     by _update_opp_attack_tracking() inside the inner policy during imagined
     rollouts -- same leak risk, same fix.

Output: patch_tb_arch.txt = `my_deck = read_deck_csv()` + adapted _TB, ready
for scripts/build_submission.py --patch (build order main(renamed)+patch+SAFETY
matches v014's build exactly).
"""
from __future__ import annotations
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TB_PATH = os.path.join(ROOT, "workspace", "exp035_turnbeam", "tb_patch.py")

src = open(TB_PATH).read()
m = re.search(r"_TB = '''(.*?)'''", src, re.S)
assert m, "tb block not found"
tb = m.group(1)

CFG = {"TB_K": int(os.environ.get("TB_K", "2")),
       "TB_BEAM": int(os.environ.get("TB_BEAM", "5")),
       "TB_BRANCH": int(os.environ.get("TB_BRANCH", "10")),
       "TB_MAXSTEPS": int(os.environ.get("TB_MAXSTEPS", "900"))}
for k, v in CFG.items():
    tb = tb.replace(f"__{k}__", str(v))
tb = (tb.replace("__TB_VALUE__", "0")
        .replace("__TB_VALUE_NPZ__", "None")
        .replace("__TB_VALUE_MARGIN__", "30"))

old_save = '''        _rev_save = dict(_rev)            # revenge cross-turn tracker: shield from
        try:                              # imagined states seen during search'''
new_save = '''        _arch_save = (_opp_last_attack_id, list(_cur_turn_logs))
        try:                              # shield pilot cross-turn globals from imagined states'''
assert old_save in tb
tb = tb.replace(old_save, new_save)

old_restore = '''        finally:
            _rev.clear()
            _rev.update(_rev_save)'''
new_restore = '''        finally:
            _opp_last_attack_id = _arch_save[0]
            _cur_turn_logs[:] = _arch_save[1]'''
assert old_restore in tb
tb = tb.replace(old_restore, new_restore)

old_def = "def _base_agent(obs_dict):\n    sel_out = _tb_inner(obs_dict)"
new_def = ("def _base_agent(obs_dict):\n    global _opp_last_attack_id\n"
           "    sel_out = _tb_inner(obs_dict)")
assert old_def in tb
tb = tb.replace(old_def, new_def)

out = os.path.join(HERE, "patch_tb_arch.txt")
open(out, "w").write("my_deck = read_deck_csv()\n" + tb)
print("wrote", out, f"({CFG})")
