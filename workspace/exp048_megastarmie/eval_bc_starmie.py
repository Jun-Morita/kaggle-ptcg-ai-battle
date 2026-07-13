"""exp048(a) decisive gate -- pilot the Mega Starmie ex/Froslass ex deck with
the freshly-trained BC net (exp041_pilotnet/results/starmie_pre1/model_ep*.pth,
trained on tomatomato+taksai's real ladder decisions, oracle_free-capable via
opp-drop) and compare to the two earlier exp048(b) heuristic-patch data points
against v016-wall (same opponent, same deck, same harness convention):
  generic lucario_v2 pilot            -> 0.825
  hand-tuned megastarmie_policy.py    -> 0.933
Usage: uv run python eval_bc_starmie.py [model_path] [n]
"""
from __future__ import annotations
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
PILOTNET = os.path.join(WS, "exp041_pilotnet")
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))
sys.path.insert(0, os.path.join(WS, "exp007_anti_crustle"))
sys.path.insert(0, PILOTNET)

import json  # noqa: E402
import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import anti_crustle as AC  # noqa: E402
from eval_raw import make_raw_agent, run_matchup  # noqa: E402


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        PILOTNET, "results", "starmie_pre1", "model_ep6.pth")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    my_deck = json.load(open(os.path.join(ROOT, "workspace", "exp011_meta_watch", "tomatomato_deck.json")))
    opp_deck = list(AC.CRUSTLE_DECK)

    def opp_factory(deck):
        return AC.make_crustle_agent()

    t0 = time.time()
    w, l, d, e = run_matchup(model, my_deck, opp_deck, opp_factory, n,
                              agent_factory=lambda m, md, od: make_raw_agent(m, md, od, oracle_free=True))
    dt = time.time() - t0
    wr = w / n if n else 0.0
    print(f"model={os.path.basename(model_path)} vs v016-wall(crustle), n={n}, oracle_free=True")
    print(f"  win={w} loss={l} draw={d} err={e}  winrate={wr:.3f}  ({dt:.0f}s, {dt/n:.2f}s/game)")
    print("reference points (same opponent, same deck, exp048(b)):")
    print("  generic lucario_v2 pilot          -> 0.825")
    print("  hand-tuned megastarmie_policy.py  -> 0.933")


if __name__ == "__main__":
    main()
