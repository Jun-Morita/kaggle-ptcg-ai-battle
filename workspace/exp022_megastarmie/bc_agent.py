"""BC agent: imitate tomatomato on MAIN piloting decisions, generic policy elsewhere.

Hybrid — the learned ranker drives the decisions where the piloting knack lives (MAIN,
single-pick: which evolve/attach/attack/retreat); the stock lucario_v2 policy handles
mechanical selections (setup, discards, coin flips) it wasn't trained on. Tests whether
imitation beats the generic floor (non-ex 0.825 / ex 0.475 / Crustle 0.10 / dragapult 0.50).
"""
from __future__ import annotations
import importlib.util
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _p in (os.path.join(ROOT, "workspace", "exp001_harness"),
           os.path.join(ROOT, "workspace", "exp013_router")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bc_dataset as BD  # state_feats / option_feats
import bc_train as BT    # Ranker
import router_policy as R

DEV = "cpu"  # tiny MLP, per-move on a handful of options -> CPU is plenty & avoids GPU contention


def _load_model():
    ck = torch.load(os.path.join(HERE, "results", "bc_model.pt"), map_location=DEV)
    m = BT.Ranker(ck["d"]).to(DEV)
    m.load_state_dict(ck["state"])
    m.eval()
    return m


def make_agent(deck):
    model = _load_model()
    spec = importlib.util.spec_from_file_location("bc_base", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    def agent(obs_dict):
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        if sel is None:
            return list(deck)
        opts = sel.get("option", [])
        # BC drives MAIN single-pick decisions with a real choice
        if sel.get("context") == 0 and sel.get("maxCount") == 1 and len(opts) >= 2 and len(opts) != 60:
            try:
                sf = BD.state_feats(obs_dict)
                rows = np.stack([np.concatenate([sf, BD.option_feats(o, obs_dict)]) for o in opts])
                with torch.no_grad():
                    sc = model(torch.tensor(rows, dtype=torch.float32, device=DEV))
                return [int(sc.argmax().item())]
            except Exception:
                pass  # fall through to generic on any parse issue
        return mod.agent(obs_dict)

    return agent


if __name__ == "__main__":
    import json
    from harness import load_engine, run_gauntlet
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp002_baselines"))
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp007_anti_crustle"))
    load_engine()
    import anti_crustle as AC
    import baselines as B

    deck = json.load(open(os.path.join(HERE, "starmie_deck.json")))

    def load_built(d):
        s = importlib.util.spec_from_file_location("b_" + os.path.basename(d), os.path.join(d, "main.py"))
        m = importlib.util.module_from_spec(s)
        p = os.getcwd()
        try:
            os.chdir(d); s.loader.exec_module(m)
        finally:
            os.chdir(p)
        return m.agent

    v006 = load_built(os.path.join(ROOT, "workspace", "exp012_nonex", "build_v006"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    bc = make_agent(deck)
    opps = [("v006 non-ex (generic floor 0.825)", lambda: v006),
            ("lucario_ex (floor 0.475)", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("Crustle (floor 0.10)", AC.make_crustle_agent),
            ("dragapult (floor 0.50)", lambda: B.make_policy_agent("dragapult"))]
    print(f"BC Mega-Starmie agent vs field (n={n}):")
    for name, mk in opps:
        st = run_gauntlet(bc, mk(), n_games=n, swap_sides=True)
        print(f"  vs {name:34s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err=({st.errors0},{st.errors1})")
