"""exp050 -- build the v020 variant with the learned state-conditioned DISCARD
chooser (SEARCH_PRI recipe, exp043/047 lineage) spliced into the public
Archaludon pilot's choose_options.

Training data: pooled DISCARD decisions of ShumpeiNomura/Canon/Takaaki Matsuda
(818 decisions/469 games, top mixed_ex4 players; val top-1 0.569-0.608 vs
static-most-discarded 0.549). NOTE the feature vector replicates exp043's
make_feats exactly, INCLUDING the two Trevenant-line features which are
constant 0 on Archaludon states (the model was trained with them at 0).

Copies exp049/build_arch, appends the override after everything (agent was
renamed _base_agent by build_submission.py; choose_options is resolved at call
time via module globals, so a tail redefinition takes effect), retars.
Includes a fire counter (_SPD_STATS) per disc-721338's "instrument so 'never
fires' is distinguishable from 'fires wrong'" lesson -- printable in local
eval, harmless in the sandbox.
"""
from __future__ import annotations
import os
import shutil
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC_BUILD = os.path.join(ROOT, "workspace", "exp049_archaludon", "build_arch")
OUT = os.path.join(HERE, "build_discard")

z = np.load(os.path.join(HERE, "results", "discard1", "pri.npz"))
tbl = {int(c): (float(b), tuple(float(x) for x in w))
       for c, b, w in zip(z["cards"], z["b"], z["W"])}
lit = "{" + ", ".join(f"{c}: ({b!r}, {w!r})" for c, (b, w) in sorted(tbl.items())) + "}"

PATCH = f'''

# ===== exp050 learned state-conditioned DISCARD chooser (SEARCH_PRI recipe) =====
_SPD_TBL = {lit}
_SPD_U = {tuple(float(x) for x in z["u"])!r}
_SPD_STOP_B = {float(z["b_stop"][0])!r}
_SPD_STOP_W = {tuple(float(x) for x in z["w_stop"])!r}
_SPD_STATS = {{"fired": 0, "fallback": 0}}
_spd_orig_choose_options = choose_options

def _spd_feats(obs):
    cur = obs.current
    yi = cur.yourIndex
    me, op = cur.players[yi], cur.players[1 - yi]
    act = (me.active or [None])[0]
    act_energy = len(act.energies or []) if act is not None else 0
    return (
        min(cur.turn, 30) / 30.0,
        len(me.hand or []) / 10.0,
        me.deckCount / 60.0,
        len(me.prize or []) / 6.0,
        len(op.prize or []) / 6.0,
        (len(me.prize or []) - len(op.prize or [])) / 6.0,
        len(me.bench or []) / 5.0,
        len(op.bench or []) / 5.0,
        0.0,
        1.0 if cur.energyAttached else 0.0,
        1.0 if cur.supporterPlayed else 0.0,
        0.0,
        min(act_energy, 3) / 3.0,
        1.0,
    )

def choose_options(obs):
    sel = obs.select
    if sel.context != SelectContext.DISCARD or not sel.option:
        return _spd_orig_choose_options(obs)
    cids = []
    for opt in sel.option:
        card = option_card(obs, opt)
        cid = getattr(card, "id", None)
        if cid is None or cid not in _SPD_TBL:
            _SPD_STATS["fallback"] += 1
            return _spd_orig_choose_options(obs)
    # second pass only after full validation
        cids.append(cid)
    cur = obs.current
    yi = cur.yourIndex
    me = cur.players[yi]
    hand_c, fld_c, dsc_c = {{}}, {{}}, {{}}
    for c in (me.hand or []):
        hand_c[c.id] = hand_c.get(c.id, 0) + 1
    for zone in (me.active or []), (me.bench or []):
        for m in zone:
            if m is None:
                continue
            fld_c[m.id] = fld_c.get(m.id, 0) + 1
            for s in (getattr(m, "preEvolution", None) or []):
                fld_c[s.id] = fld_c.get(s.id, 0) + 1
    for c in (me.discard or []):
        dsc_c[c.id] = dsc_c.get(c.id, 0) + 1
    f = _spd_feats(obs)
    scores = []
    for cid in cids:
        b, w = _SPD_TBL[cid]
        s = b + sum(wi * fi for wi, fi in zip(w, f))
        s += (_SPD_U[0] * min(hand_c.get(cid, 0), 3) / 3.0
              + _SPD_U[1] * min(fld_c.get(cid, 0), 3) / 3.0
              + _SPD_U[2] * min(dsc_c.get(cid, 0), 3) / 3.0)
        scores.append(s)
    stop = _SPD_STOP_B + sum(wi * fi for wi, fi in zip(_SPD_STOP_W, f))
    order = sorted(range(len(cids)), key=lambda i: -scores[i])
    out = []
    for i in order:
        if len(out) >= sel.maxCount:
            break
        if len(out) >= sel.minCount and scores[i] <= stop:
            break
        out.append(i)
    if len(out) < sel.minCount:
        _SPD_STATS["fallback"] += 1
        return _spd_orig_choose_options(obs)
    _SPD_STATS["fired"] += 1
    return out
'''

if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC_BUILD, OUT, ignore=shutil.ignore_patterns("__pycache__", "*.tar.gz"))
main_p = os.path.join(OUT, "main.py")
open(main_p, "a").write(PATCH)

tarp = os.path.join(OUT, "submission.tar.gz")
with tarfile.open(tarp, "w:gz") as tar:
    tar.add(main_p, arcname="main.py")
    tar.add(os.path.join(OUT, "deck.csv"), arcname="deck.csv")
    cgd = os.path.join(OUT, "cg")
    for root, _, files in os.walk(cgd):
        for fn in files:
            if fn.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(root, fn)
            tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, cgd)))
print("built", tarp)
