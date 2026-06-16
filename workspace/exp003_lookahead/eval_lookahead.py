"""Evaluate the Search-API lookahead agent against baseline opponents.

Compares both modes (1-ply vs greedy-turn-rollout) to the exp002 strength bar.

Usage: uv run python eval_lookahead.py [n_games]
"""
from __future__ import annotations

import json
import os
import sys
import time

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import run_gauntlet  # noqa: E402
from agent_lookahead import make_lookahead_agent  # noqa: E402
from baselines import make_policy_agent, make_random_agent_with_deck, DECKS  # noqa: E402
from kaggle_agent_template.repro import set_seed  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
DECK = DECKS["lucario_v2"]  # use the strongest baseline deck for a fair comparison


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    set_seed(42)
    opponents = {
        "random": make_random_agent_with_deck(DECK, seed=0),
        "dragapult": make_policy_agent("dragapult"),
        "lucario_v1": make_policy_agent("lucario_v1"),
        "lucario_v2": make_policy_agent("lucario_v2"),
    }
    out = {"n_games": n, "deck": "lucario_v2", "modes": {}}
    for mode_name, rollout in [("one_ply", False), ("turn_rollout", True)]:
        look = make_lookahead_agent(DECK, seed=1, rollout=rollout)
        res = {}
        wrs = []
        for opp_name, opp in opponents.items():
            t0 = time.perf_counter()
            st = run_gauntlet(look, opp, n_games=n, swap_sides=True)
            dt = time.perf_counter() - t0
            res[opp_name] = {
                "winrate": round(st.winrate0, 3),
                "record": f"{st.wins0}-{st.wins1}-{st.draws}",
                "max_move_s": round(st.max_move_time0, 3),
                "s_per_game": round(dt / n, 3),
            }
            if opp_name != "random":
                wrs.append(st.winrate0)
            print(f"[{mode_name}] vs {opp_name:11s} winrate={st.winrate0:.3f} "
                  f"({st.wins0}-{st.wins1}-{st.draws}) maxmove={st.max_move_time0:.2f}s "
                  f"{dt/n:.2f}s/game")
        res["avg_vs_rulebased"] = round(sum(wrs) / len(wrs), 3)
        out["modes"][mode_name] = res
        print(f"[{mode_name}] avg vs rule-based = {res['avg_vs_rulebased']:.3f} "
              f"(bar to beat: lucario_v2 0.680)\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "lookahead_eval.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved -> {os.path.join(RESULTS_DIR, 'lookahead_eval.json')}")


if __name__ == "__main__":
    main()
