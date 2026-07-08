"""exp041 Phase 3 -- MCTS (exp040's mcts_agent, fixed exclusion determinization)
on top of the PRETRAINED net, evaluated on the same 5-matchup field and
directly comparable to eval_raw.py (same conditions, same pilot_ref).

Gate (SESSION_NOTES Phase 3): MCTS must beat the raw net's total (1.660 for
model_ep2); "more search = worse" here would mean the value head's quality
still doesn't support search (exp010/exp040 pattern) despite the good AUC.

Usage: uv run python eval_mcts.py results/pre1/model_ep2.pth --n 50 --search-count 16
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
from teacher_pool import build_teacher_pool  # noqa: E402
from eval_raw import run_matchup  # noqa: E402  (same game loop, same conditions)


def make_mcts_agent_factory(search_count):
    def make(model, my_deck, opp_deck):
        def agent(obs_dict):
            sel, _ = tm.mcts_agent(obs_dict, my_deck, model, search_count,
                                   opp_deck=opp_deck)
            return sel
        return agent
    return make


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_path")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--search-count", type=int, default=16)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--only", default=None, help="limit to one matchup name")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(args.d_model, 2, args.d_model * 2, 1, 1).to(device)
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.eval()

    my_deck = tm.load_deck("charmq")
    pilot_ref = {"crustle": 0.827, "ex_lucario": 0.775, "dragapult": 0.160,
                 "archaludon": 0.158, "mirror_revenge": 0.576}

    factory = make_mcts_agent_factory(args.search_count)
    out = {}
    t0 = time.time()
    with torch.no_grad():
        for name, opp_deck, opp_factory, _ in build_teacher_pool(my_deck):
            if name not in pilot_ref:
                continue
            if args.only and name != args.only:
                continue
            w, l, d, e = run_matchup(model, my_deck, opp_deck, opp_factory, args.n,
                                     agent_factory=factory)
            wr = w / max(w + l + d, 1)
            out[name] = {"wr": round(wr, 3), "record": f"{w}-{l}-{d}", "errors": e,
                         "pilot_ref": pilot_ref[name]}
            print(f"{name:15s} mcts{args.search_count}={wr:.3f} ({w}-{l}-{d}, err={e}) "
                  f"pilot_ref={pilot_ref[name]}", flush=True)
    total = sum(v["wr"] for v in out.values())
    print(f"TOTAL mcts{args.search_count}={total:.3f} pilot_ref={sum(pilot_ref.values()):.3f} "
          f"({time.time()-t0:.0f}s)")
    json.dump(out, open(os.path.join(os.path.dirname(args.model_path),
                                     f"eval_mcts{args.search_count}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
