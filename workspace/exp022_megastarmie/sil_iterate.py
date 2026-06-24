"""Self-Imitation Learning for Mega-Starmie piloting — a value-free RL approach.

Motivated by WHY prior learning failed:
  - value nets can't read the mid-game (exp014 AUC<0.70) -> avoid value/Q entirely.
  - BC error-accumulates + distribution-shifts (exp022) -> train on the agent's OWN
    state distribution and keep only WINNING decisions (self-imitation).
  - cold-start self-play collapses (exp010) -> warm-start from the BC policy.
Loop: roll out current policy vs the FIELD pool (not the mirror), epsilon-greedy for
diversity; keep decisions from WON games; retrain the ranker on (expert BC + own wins);
evaluate vs the field. Reinforces winning lines on-distribution without a value net.

Usage: uv run python sil_iterate.py [iters] [games_per_opp_per_side]
"""
from __future__ import annotations
import importlib.util
import os
import sys

import numpy as np
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _p in (os.path.join(ROOT, "workspace", "exp001_harness"),
           os.path.join(ROOT, "workspace", "exp002_baselines"),
           os.path.join(ROOT, "workspace", "exp007_anti_crustle"),
           os.path.join(ROOT, "workspace", "exp013_router")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bc_dataset as BD
import bc_train as BT
import router_policy as R
from harness import load_engine, run_match, run_gauntlet

load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa

DEV = "cuda" if torch.cuda.is_available() else "cpu"
RNG = np.random.default_rng(0)


def load_generic_base(deck):
    spec = importlib.util.spec_from_file_location("sil_base", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def make_logging_agent(model, mod, deck, buf, eps=0.0):
    def agent(obs_dict):
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        if sel is None:
            return list(deck)
        opts = sel.get("option", [])
        if sel.get("context") == 0 and sel.get("maxCount") == 1 and 2 <= len(opts) != 60:
            try:
                sf = BD.state_feats(obs_dict)
                of = [BD.option_feats(o, obs_dict) for o in opts]
                rows = np.stack([np.concatenate([sf, o]) for o in of])
                with torch.no_grad():
                    sc = model(torch.tensor(rows, dtype=torch.float32, device=DEV))
                pick = int(RNG.integers(len(opts))) if RNG.random() < eps else int(sc.argmax().item())
                buf.append((rows.astype(np.float32), pick))   # rows already include state+option
                return [pick]
            except Exception:
                pass
        return mod.agent(obs_dict)
    return agent


def collect(model, mod, deck, opps, games, eps):
    """Play vs field pool; return winning decisions as (X_rows, groups, y)."""
    Xw, gw, yw = [], [], []
    wins = total = 0
    for name, mk in opps:
        for side in (0, 1):
            for _ in range(games):
                buf = []
                me = make_logging_agent(model, mod, deck, buf, eps=eps)
                opp = mk()
                r = run_match(me, opp) if side == 0 else run_match(opp, me)
                total += 1
                won = (r.winner == side)
                wins += int(won)
                if won:
                    for rows, pick in buf:
                        Xw.append(rows)
                        gw.append(len(rows))
                        yw.append(pick)
    return Xw, gw, yw, wins / max(1, total)


def train_ranker(X, groups, y, d, epochs=40, init=None):
    offs = np.concatenate([[0], np.cumsum(groups)])
    n = len(groups)
    Xt = torch.tensor(X, device=DEV)
    model = BT.Ranker(d).to(DEV)
    if init is not None:
        model.load_state_dict(init)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3, weight_decay=1e-5)
    ids = list(range(n))
    for _ in range(epochs):
        RNG.shuffle(ids)
        for b in range(0, n, 256):
            opt.zero_grad()
            loss = 0.0
            for i in ids[b:b + 256]:
                s, e = offs[i], offs[i + 1]
                sc = model(Xt[s:e])
                loss = loss + nn.functional.cross_entropy(sc.unsqueeze(0),
                              torch.tensor(int(y[i]), device=DEV).unsqueeze(0))
            loss.backward()
            opt.step()
    model.eval()
    return model


def eval_field(agent_factory, opps, n=40):
    out = {}
    for name, mk in opps:
        st = run_gauntlet(agent_factory(), mk(), n_games=n, swap_sides=True)
        out[name] = st.winrate0
    return out


def main():
    import json
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    deck = json.load(open(os.path.join(HERE, "starmie_deck.json")))
    mod = load_generic_base(deck)

    # expert BC data (anti-forgetting anchor)
    d = np.load(os.path.join(HERE, "results", "bc_data.npz"))
    Xe, ge, ye = d["X"], d["groups"], d["y"]
    dim = Xe.shape[1]
    # expert rows as list-of-arrays for concatenation with own-wins
    offs = np.concatenate([[0], np.cumsum(ge)])
    Xe_rows = [Xe[offs[i]:offs[i + 1]] for i in range(len(ge))]

    # warm start: the BC model
    ck = torch.load(os.path.join(HERE, "results", "bc_model.pt"), map_location=DEV)
    model = BT.Ranker(dim).to(DEV)
    model.load_state_dict(ck["state"])
    model.eval()

    v006 = None
    bdir = os.path.join(ROOT, "workspace", "exp012_nonex", "build_v006")
    spec = importlib.util.spec_from_file_location("v006b", os.path.join(bdir, "main.py"))
    m6 = importlib.util.module_from_spec(spec)
    p = os.getcwd()
    try:
        os.chdir(bdir); spec.loader.exec_module(m6)
    finally:
        os.chdir(p)
    v006 = m6.agent
    opps = [("v006_nonex", lambda: v006),
            ("lucario_ex", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("crustle", AC.make_crustle_agent),
            ("dragapult", lambda: B.make_policy_agent("dragapult"))]

    def factory(mdl):
        return lambda: make_logging_agent(mdl, mod, deck, [], eps=0.0)

    print(f"=== SIL: warm-start BC, {iters} iters x {games} games/opp/side vs FIELD ===")
    print("iter0 (BC):", {k: round(v, 3) for k, v in eval_field(factory(model), opps).items()})

    own_X, own_g, own_y = [], [], []
    for it in range(1, iters + 1):
        Xw, gw, yw, wr = collect(model, mod, deck, opps, games, eps=0.15)
        own_X += Xw; own_g += gw; own_y += yw
        # train on expert anchor + accumulated own wins
        allX = np.concatenate(Xe_rows + own_X) if own_X else Xe
        allg = np.concatenate([ge, np.array(own_g, dtype=np.int32)]) if own_g else ge
        ally = np.concatenate([ye, np.array(own_y, dtype=np.int32)]) if own_y else ye
        model = train_ranker(allX, allg, ally, dim, epochs=30,
                             init=model.state_dict())
        res = eval_field(factory(model), opps)
        print(f"iter{it}: collect_wr={wr:.3f} own_win_decisions={len(own_y)} | "
              f"eval={{ {', '.join(f'{k}:{v:.3f}' for k,v in res.items())} }}")
        torch.save({"state": model.state_dict(), "d": dim},
                   os.path.join(HERE, "results", f"sil_model_it{it}.pt"))


if __name__ == "__main__":
    main()
