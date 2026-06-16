"""Round-robin matchup table for the baseline rule-based agents (+ random).

Each pair plays `n_games` with sides swapped for fairness. Produces a win-rate
matrix (row agent's win rate vs column agent) and saves it to results/.

Usage: uv run python run_matchups.py [n_games]
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
if EXP1 not in sys.path:
    sys.path.insert(0, EXP1)

from harness import run_gauntlet  # noqa: E402
from baselines import (  # noqa: E402
    DECKS,
    POLICY_NAMES,
    make_policy_agent,
    make_random_agent_with_deck,
)
from kaggle_agent_template.repro import set_seed  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def main() -> None:
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    set_seed(42)

    agents = {name: make_policy_agent(name) for name in POLICY_NAMES}
    # random uses lucario_v2's (legal) deck so battle_start always succeeds
    agents["random"] = make_random_agent_with_deck(DECKS["lucario_v2"], seed=123)
    names = list(agents.keys())

    winrate = {a: {b: None for b in names} for a in names}
    detail = {}
    t0 = time.perf_counter()
    for a, b in itertools.combinations(names, 2):
        st = run_gauntlet(agents[a], agents[b], n_games=n_games, swap_sides=True)
        wr = st.winrate0
        winrate[a][b] = round(wr, 3)
        winrate[b][a] = round(1.0 - wr, 3)
        detail[f"{a}_vs_{b}"] = {
            "winrate_a": round(wr, 3),
            "a_wins": st.wins0, "b_wins": st.wins1, "draws": st.draws,
            "errors_a": st.errors0, "errors_b": st.errors1,
            "avg_moves": round(st.total_moves / st.n, 1),
            "reasons": st.reasons,
        }
        print(f"{a:11s} vs {b:11s}  {a} winrate={wr:.3f}  "
              f"(w{st.wins0}-{st.wins1}-d{st.draws}) avg_moves={st.total_moves/st.n:.0f}")
    dt = time.perf_counter() - t0

    # win-rate matrix + average win rate (strength ranking)
    print(f"\n=== Win-rate matrix (row vs col), n={n_games}/pair, {dt:.0f}s ===")
    hdr = "             " + " ".join(f"{n[:9]:>9s}" for n in names)
    print(hdr)
    avg = {}
    for a in names:
        cells = []
        vals = []
        for b in names:
            if a == b:
                cells.append(f"{'—':>9s}")
            else:
                cells.append(f"{winrate[a][b]:>9.3f}")
                vals.append(winrate[a][b])
        avg[a] = sum(vals) / len(vals)
        print(f"{a:11s}  " + " ".join(cells))
    print("\n=== Average win rate (overall strength) ===")
    for a, v in sorted(avg.items(), key=lambda kv: -kv[1]):
        print(f"  {a:12s} {v:.3f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = {
        "n_games_per_pair": n_games,
        "agents": names,
        "winrate_matrix": winrate,
        "avg_winrate": {k: round(v, 3) for k, v in avg.items()},
        "detail": detail,
        "wall_time_s": round(dt, 1),
    }
    with open(os.path.join(RESULTS_DIR, "matchups.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nsaved -> {os.path.join(RESULTS_DIR, 'matchups.json')}")


if __name__ == "__main__":
    main()
