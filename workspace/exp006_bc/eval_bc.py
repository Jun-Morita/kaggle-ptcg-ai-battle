"""Evaluate the behavior-cloned net (greedy, no search) vs the exp002 pool.

Usage: uv run python eval_bc.py results/bc_model.pth [n_games]
"""
from __future__ import annotations

import json
import os
import sys
import time

import torch

HERE = os.path.dirname(__file__)
EXP1 = os.path.abspath(os.path.join(HERE, "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(HERE, "..", "exp002_baselines"))
EXP4 = os.path.abspath(os.path.join(HERE, "..", "exp004_mcts"))
for p in (EXP1, EXP2, EXP4):
    if p not in sys.path:
        sys.path.insert(0, p)

import train_mcts as T  # noqa: E402
from harness import run_gauntlet  # noqa: E402
from baselines import make_policy_agent, make_random_agent_with_deck, DECKS  # noqa: E402
from train_bc import enumerate_actions  # noqa: E402


def make_bc_agent(deck, model):
    """Greedy policy: pick the action the net scores highest. Crash-safe."""
    def agent(obs_dict):
        try:
            obs = T.to_observation_class(obs_dict)
            if obs.select is None:
                return list(deck)
            select = obs.select
            actions = enumerate_actions(select)
            if len(actions) == 1:
                return actions[0]
            sv_enc = T.get_encoder_input(obs, deck)
            sv_dec = T.get_decoder_input(obs, actions)
            _, policy = T.eval_nn(sv_enc, sv_dec, model)
            best = max(range(len(actions)), key=lambda i: policy[i])
            sel = actions[best]
            n = len(select.option)
            if all(0 <= i < n for i in sel) and len(set(sel)) == len(sel) \
                    and select.minCount <= len(sel) <= select.maxCount:
                return sel
        except Exception:
            pass
        # fallback: first minCount legal indices
        n = len(obs_dict.get("select", {}).get("option", []) or [])
        try:
            select = T.to_observation_class(obs_dict).select
            n = len(select.option)
            k = min(max(1, select.minCount), n) if n else 0
            return list(range(k))
        except Exception:
            return [0]
    agent.__name__ = "agent_bc"
    return agent


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "bc_model.pth")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    deck = DECKS["lucario_v2"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print(f"loaded {model_path} on {device}; n={n}/opp")

    opponents = {
        "random": make_random_agent_with_deck(deck, seed=0),
        "dragapult": make_policy_agent("dragapult"),
        "lucario_v1": make_policy_agent("lucario_v1"),
        "lucario_v2": make_policy_agent("lucario_v2"),
    }
    bc = make_bc_agent(deck, model)
    res, wrs = {}, []
    with torch.inference_mode():
        for name, opp in opponents.items():
            t0 = time.perf_counter()
            st = run_gauntlet(bc, opp, n_games=n, swap_sides=True)
            dt = time.perf_counter() - t0
            res[name] = {"winrate": round(st.winrate0, 3), "record": f"{st.wins0}-{st.wins1}-{st.draws}",
                         "errors": st.errors0, "max_move_s": round(st.max_move_time0, 3),
                         "s_per_game": round(dt / n, 2)}
            if name != "random":
                wrs.append(st.winrate0)
            print(f"vs {name:11s} winrate={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err={st.errors0} maxmove={st.max_move_time0:.3f}s {dt/n:.2f}s/game")
    avg = round(sum(wrs) / len(wrs), 3)
    print(f"\navg vs rule-based = {avg:.3f}  (teacher lucario_v2 ~0.68; bar 0.680)")
    out = {"model": os.path.basename(model_path), "n_games": n, "results": res, "avg_vs_rulebased": avg}
    with open(os.path.join(HERE, "results", "bc_pool_eval.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("saved -> results/bc_pool_eval.json")


if __name__ == "__main__":
    main()
