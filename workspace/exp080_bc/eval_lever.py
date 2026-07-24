"""exp080 Front-2 lever measurement -- BEFORE building a multi-day AlphaZero
self-play/MCTS loop, measure the lever cleanly: does MCTS on top of the Grimmsnarl
BC net BEAT its own raw argmax?

The cleanest, confound-free test is a SELF-MIRROR: net-with-MCTS (seat A) vs
net-with-raw-argmax (seat B), same Grimmsnarl deck both sides, seat-alternated.
No opponent-pilot-strength confound (that invalidated the pub1034 gate) because
it is the net against ITSELF, search being the only difference. If MCTS wins
> ~0.55, search improves this net's play (exp041 Phase-3 pattern, worth building
the loop). If <= 0.5, the value head does not support search (exp010/exp040
"more search = worse", kill the loop and save days).

Usage: uv run python eval_lever.py [model.pth] [n] [--sc 16]
"""
from __future__ import annotations
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402


def main():
    model_path = next((a for a in sys.argv[1:] if a.endswith(".pth")),
                      os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm10", "model_ep2.pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 40)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16

    grimm = json.load(open(os.path.join(HERE, "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    mcts_factory = make_mcts_agent_factory(sc, oracle_free=True)          # seat "ours"
    raw_opp = lambda deck: ER.make_raw_agent(model, deck, deck, oracle_free=True)  # seat "opp"

    print(f"LEVER (self-mirror)  net={os.path.relpath(model_path, WS)}  "
          f"MCTS(sc={sc}) vs raw-argmax  Grimmsnarl both sides  n={n}\n", flush=True)
    t0 = time.time()
    w, l, d, e = ER.run_matchup(model, grimm, grimm, raw_opp, n, agent_factory=mcts_factory)
    played = w + l + d
    wr = w / played if played else 0.0
    print(f"MCTS-net vs raw-net: {w}-{l}-{d}  errors={e}  MCTS winrate={wr:.3f}  ({time.time()-t0:.0f}s)")
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"z vs 0.5 = {z:+.2f}")
    print("VERDICT:", "MCTS lever POSITIVE (search improves the net) -> build the AlphaZero loop"
          if wr >= 0.55 else
          ("MCTS lever FLAT (~0.5) -> search doesn't help; do NOT build the loop"
           if wr >= 0.45 else
           "MCTS lever NEGATIVE (search makes it WORSE, exp010 pattern) -> do NOT build the loop"))
    json.dump({"model": model_path, "n": n, "sc": sc, "w": w, "l": l, "d": d, "err": e, "mcts_wr": wr, "z": z},
              open(os.path.join(HERE, f"lever_mirror_sc{sc}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
