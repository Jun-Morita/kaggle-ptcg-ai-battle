"""exp080 post-gate hole-check -- the RAW BC net piloting Grimmsnarl vs pub1034
across the top-band opponent spread (Alakazam / TR Spidops / crustle / dragapult),
weighted by the silver-band shares. A submission plays the whole ladder, so a
mirror-only PASS could still hide a catastrophic hole (e.g. dragapult 0.1) that
tanks the score. This is the cheap check before building a submission.

net always pilots the canonical Grimmsnarl (modal) list. Opponent pilots each
archetype's modal list under pub1034. Seat-alternated. oracle-free (ship cond).

Usage: uv run python eval_spread.py [model.pth] [n_per_matchup]
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
import eval_gate as EG  # noqa: E402  (make_pub1034 + raw_oraclefree)

# silver-band shares (exp080 scan); mirror handled by eval_gate separately
SHARE = {"mixed_ex3": 0.43, "mixed_ex1": 0.28, "mixed_ex2": 0.18,
         "crustle_control": 0.08, "dragapult": 0.07}
LABEL = {"mixed_ex1": "Alakazam", "mixed_ex2": "TR Spidops",
         "crustle_control": "Crustle", "dragapult": "Dragapult", "mixed_ex3": "Grimmsnarl(mirror)"}


def main():
    model_path = next((a for a in sys.argv[1:] if a.endswith(".pth")),
                      os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm1", "model_ep2.pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 100)

    grimm = json.load(open(os.path.join(HERE, "grimmsnarl_deck.json")))
    opp_decks = json.load(open(os.path.join(HERE, "opp_decks.json")))
    opp_decks["mixed_ex3"] = grimm  # include the mirror for a full weighted total

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    print(f"SPREAD  net={os.path.relpath(model_path, WS)}  deck=Grimmsnarl(modal)  "
          f"opp=pub1034  n={n}/matchup\n", flush=True)
    print(f"{'matchup':22}{'share':>7}{'W-L-D':>12}{'winrate':>9}")
    rows, wsum = {}, 0.0
    for mu in ["mixed_ex3", "mixed_ex1", "mixed_ex2", "crustle_control", "dragapult"]:
        w, l, d, e = ER.run_matchup(model, grimm, opp_decks[mu], EG.make_pub1034, n,
                                    agent_factory=EG.raw_oraclefree)
        wr = w / (w + l + d) if (w + l + d) else 0.0
        rows[mu] = {"w": w, "l": l, "d": d, "err": e, "wr": wr}
        wsum += SHARE[mu] * wr
        flag = "  <-- HOLE" if wr < 0.40 else ""
        print(f"{LABEL[mu]:22}{SHARE[mu]:7.2f}{f'{w}-{l}-{d}':>12}{wr:9.3f}  err={e}{flag}", flush=True)
    print(f"\nshare-weighted winrate = {wsum:.3f}")
    json.dump({"model": model_path, "n": n, "rows": rows, "weighted": wsum},
              open(os.path.join(HERE, f"spread_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
