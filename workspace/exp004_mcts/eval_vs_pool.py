"""Evaluate a trained MCTS model against the exp002 baseline pool.

Wraps mcts_agent as a harness agent and plays vs random / dragapult /
lucario_v1 / lucario_v2. Reports avg win rate vs the rule-based opponents and
compares to the bar (lucario_v2 0.680).

Usage: uv run python eval_vs_pool.py results/model_gen4.pth [n_games] [search_count]
"""
from __future__ import annotations

import json
import os
import sys
import time

import torch

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import run_gauntlet  # noqa: E402
from baselines import make_policy_agent, make_random_agent_with_deck, DECKS  # noqa: E402
import train_mcts as T  # noqa: E402


def make_mcts_agent(deck, model, search_count):
    def agent(obs_dict):
        obs = T.to_observation_class(obs_dict)
        if obs.select is None:
            return list(deck)
        sel, _ = T.mcts_agent(obs_dict, deck, model, search_count)
        return sel
    agent.__name__ = "agent_mcts"
    return agent


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(T.RESULTS_DIR, "model_gen4.pth")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    search_count = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    deck_name = "lucario_v2"
    deck = DECKS[deck_name]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print(f"loaded {model_path} on {device}; search_count={search_count} n={n}/opp")

    opponents = {
        "random": make_random_agent_with_deck(deck, seed=0),
        "dragapult": make_policy_agent("dragapult"),
        "lucario_v1": make_policy_agent("lucario_v1"),
        "lucario_v2": make_policy_agent("lucario_v2"),
    }
    mcts = make_mcts_agent(deck, model, search_count)
    res, wrs = {}, []
    with torch.inference_mode():
        for name, opp in opponents.items():
            t0 = time.perf_counter()
            st = run_gauntlet(mcts, opp, n_games=n, swap_sides=True)
            dt = time.perf_counter() - t0
            res[name] = {"winrate": round(st.winrate0, 3), "record": f"{st.wins0}-{st.wins1}-{st.draws}",
                         "max_move_s": round(st.max_move_time0, 3), "s_per_game": round(dt / n, 2)}
            if name != "random":
                wrs.append(st.winrate0)
            print(f"vs {name:11s} winrate={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"maxmove={st.max_move_time0:.2f}s {dt/n:.2f}s/game")
    avg = round(sum(wrs) / len(wrs), 3)
    print(f"\navg vs rule-based = {avg:.3f}  (bar: lucario_v2 0.680)")

    out = {"model": os.path.basename(model_path), "n_games": n, "search_count": search_count,
           "results": res, "avg_vs_rulebased": avg}
    with open(os.path.join(T.RESULTS_DIR, "pool_eval.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved -> {os.path.join(T.RESULTS_DIR, 'pool_eval.json')}")


if __name__ == "__main__":
    main()
