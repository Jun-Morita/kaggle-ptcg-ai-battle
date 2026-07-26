"""exp083c: re-measure the MCTS lever now that the value head actually works.

exp080 concluded "search makes this net WORSE" (self-mirror MCTS vs raw argmax:
0.300, z=-3.10) and used that to kill the AlphaZero lane. But that net was
trained on a corpus filtered to WON games only, so every value label was +1 and
the value head collapsed to a constant (measured on the shipped net: min 0.99986,
max 1.00000, stdev 0.00002). Search guided by a constant evaluator is strictly
noise, so the old result says nothing about whether search helps -- it only says
a constant value function cannot guide search.

sc083_v3t is the first net with a real value head (outcome AUC 0.63 early /
0.94 late). Same confound-free design as exp080's: the net against ITSELF, same
deck both seats, search the only difference.

Usage: ENC_V3=1 uv run python lever_v3.py <model.pth> [n] [--sc 16]
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 60)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16

    cfg = dict(LEGACY)
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    if os.path.exists(cand):
        cfg.update({k: v for k, v in json.load(open(cand)).items() if k in cfg})
    assert tm.ENC_V3 == (1 if json.load(open(cand)).get("enc_version", 1) >= 3 else 0), \
        "ENC_V3 env does not match the checkpoint's enc_version -- features would differ"

    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()

    mcts = make_mcts_agent_factory(sc, oracle_free=True)
    raw = lambda d: ER.make_raw_agent(model, d, d, oracle_free=True)  # noqa: E731
    print(f"LEVER v3  net={os.path.relpath(pth, WS)} {cfg} ENC_V3={tm.ENC_V3}\n"
          f"MCTS(sc={sc}) vs raw-argmax, self-mirror Grimmsnarl, n={n}\n", flush=True)

    t0 = time.time()
    w, l, d, e = ER.run_matchup(model, deck, deck, raw, n, agent_factory=mcts)
    played = w + l + d
    wr = w / played if played else 0.0
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"MCTS vs raw: {w}-{l}-{d}  errors={e}  MCTS winrate={wr:.3f}  z={z:+.2f}  "
          f"({time.time()-t0:.0f}s)")
    print("VERDICT:", "search HELPS now (the old 0.300 was a constant-value artifact)"
          if wr >= 0.55 else ("FLAT -- search still buys nothing" if wr >= 0.45
                              else "search still HURTS"))
    json.dump({"model": pth, "n": n, "sc": sc, "w": w, "l": l, "d": d, "err": e,
               "mcts_wr": wr, "z": z, "arch": cfg},
              open(os.path.join(HERE, "results", f"lever_v3_sc{sc}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
