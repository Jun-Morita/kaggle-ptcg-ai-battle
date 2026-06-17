"""exp008 evaluation: does belief-grounded determinization beat placeholder?

Controlled comparison of PIMC with belief (oracle opponent decklist) vs PIMC
with placeholder determinization, against the exp002 pool. Each opponent uses
its true decklist as the oracle belief (upper bound on opponent modeling).

Usage: uv run python eval_pimc.py [n_games] [k] [horizon]
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
import baselines as B  # noqa: E402
from agent_pimc import make_pimc_agent  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    horizon = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    deck = B.DECKS["lucario_v2"]

    opponents = {
        "random": (B.make_random_agent_with_deck(deck, seed=0), deck),
        "dragapult": (B.make_policy_agent("dragapult"), B.DECKS["dragapult"]),
        "lucario_v2": (B.make_policy_agent("lucario_v2"), B.DECKS["lucario_v2"]),
    }
    out = {"n": n, "k": k, "horizon": horizon, "modes": {}}
    for use_belief in (True, False):
        tag = "belief_oracle" if use_belief else "placeholder"
        res, wrs = {}, []
        for name, (opp, opp_deck) in opponents.items():
            pimc = make_pimc_agent(deck, opp_deck=opp_deck, k_rollouts=k,
                                   max_candidates=4, horizon=horizon, seed=1,
                                   use_belief=use_belief)
            t0 = time.perf_counter()
            st = run_gauntlet(pimc, opp, n_games=n, swap_sides=True)
            dt = time.perf_counter() - t0
            res[name] = {"winrate": round(st.winrate0, 3), "record": f"{st.wins0}-{st.wins1}-{st.draws}",
                         "max_move_s": round(st.max_move_time0, 1), "s_per_game": round(dt / n, 1)}
            if name != "random":
                wrs.append(st.winrate0)
            print(f"[{tag:13s}] vs {name:11s} winrate={st.winrate0:.3f} "
                  f"({st.wins0}-{st.wins1}) max_move={st.max_move_time0:.1f}s {dt/n:.1f}s/game", flush=True)
        res["avg_vs_rulebased"] = round(sum(wrs) / len(wrs), 3)
        out["modes"][tag] = res
        print(f"[{tag}] avg vs rule-based = {res['avg_vs_rulebased']:.3f} (bar 0.680)\n", flush=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "pimc_eval.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("saved -> results/pimc_eval.json")


if __name__ == "__main__":
    main()
