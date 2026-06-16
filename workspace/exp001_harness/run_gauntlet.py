"""Entry point: run a baseline gauntlet and save results.

Usage: uv run python run_gauntlet.py [n_games]
"""
from __future__ import annotations

import json
import os
import sys
import time

from harness import run_gauntlet
from agents import make_random_agent

from kaggle_agent_template.repro import set_seed

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def main() -> None:
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seed = 42
    set_seed(seed)

    agent0 = make_random_agent(seed=seed)
    agent1 = make_random_agent(seed=seed + 1)

    t0 = time.perf_counter()
    st = run_gauntlet(agent0, agent1, n_games=n_games, swap_sides=True, verbose=True)
    dt = time.perf_counter() - t0

    print("\n=== Gauntlet summary ===")
    print(st.summary())
    print(f"wall_time={dt:.2f}s  ({dt / n_games * 1000:.1f} ms/game)")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = {
        "matchup": "random_vs_random",
        "n_games": n_games,
        "seed": seed,
        "winrate_agent0": st.winrate0,
        "wins0": st.wins0,
        "wins1": st.wins1,
        "draws": st.draws,
        "errors0": st.errors0,
        "errors1": st.errors1,
        "avg_moves": st.total_moves / st.n if st.n else 0,
        "max_move_time": [st.max_move_time0, st.max_move_time1],
        "reasons": st.reasons,
        "wall_time_s": dt,
    }
    with open(os.path.join(RESULTS_DIR, "baseline_random.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved -> {os.path.join(RESULTS_DIR, 'baseline_random.json')}")


if __name__ == "__main__":
    main()
