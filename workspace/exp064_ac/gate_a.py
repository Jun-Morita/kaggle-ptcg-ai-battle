"""exp064 Gate A -- BC clone (raw argmax) vs STOCK pub1034, mirror, n CRN.

Pre-registered: wr >= 0.45 at n=600 passes (clone fidelity; the search-augmented
teacher won't be fully matched by a searchless argmax net -- 0.45 = close enough
for PPO to close the rest). Model = pre_mirror ep4 (best val acc 0.7795).
Uses the CRN harness (engine-level seed), oracle known (mirror deck symmetric).
Usage: uv run python gate_a.py [n] [model_path]
"""
from __future__ import annotations
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp041_pilotnet", "exp040_mctsv2", "exp057_pubalakazam", "exp052_crn"):
    sys.path.insert(0, os.path.join(WS, p))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
from eval_raw import make_raw_agent  # noqa: E402
from harness_crn import run_gauntlet  # noqa: E402
from datagen_mirror import make_pub, pub_deck  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    mp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        WS, "exp041_pilotnet", "results", "pre_mirror", "model_ep4.pth")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(mp, map_location=device))
    model.eval()
    deck = pub_deck()

    def net_factory():
        a = make_raw_agent(model, deck, deck)
        def agent(obs):
            if obs.get("select") is None:
                return list(deck)
            return a(obs)
        return agent

    t0 = time.time()
    st = run_gauntlet(net_factory(), make_pub(), n_games=n, swap_sides=True,
                      crn_seed_base=20260808)
    print(f"GATE A: clone vs stock mirror wr={st.winrate0:.3f} "
          f"({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1}) "
          f"{time.time()-t0:.0f}s  [pass >= 0.45]")


if __name__ == "__main__":
    main()
