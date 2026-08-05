"""Our shipped configuration against the public 911.3 agent, same 60-card deck.

The ladder says the gap is 911.3 - 845.3 = 66 points and that it is entirely
piloting: their deck.csv is our deck.csv, card for card. This measures the same
gap head-to-head, which is the one comparison where a local number and a ladder
number are asking the same question of the same two players.

It is also the first local opponent that is STRONGER than us, so unlike the
rule-based field (we score 0.89-0.99 there and 0.55 on the ladder) it cannot
saturate.

Usage: ENC_V3=1 uv run python eval_vs_ref.py <model.pth> [n] [--sc 16]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
for p in ("exp001_harness", "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402
from load_ref import make_ref_agent, DECK  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 100)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    final = sys.argv[sys.argv.index("--final") + 1] if "--final" in sys.argv else "visit_q"
    tm.FINAL_PICK = final

    arch = json.load(open(os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")))
    cfg = dict(LEGACY)
    cfg.update({k: v for k, v in arch.items() if k in cfg})
    # ENC_V4 nets carry a different encoder vocabulary (28 words / 38000 rows), so
    # the module globals have to be set BEFORE MyModel is constructed.
    v = int(arch.get("enc_version", 1))
    tm.ENC_V3 = 1 if v >= 3 else 0
    tm.ENC_V4 = 1 if v >= 4 else 0
    tm.num_words_encoder = 28 if v >= 4 else (26 if v >= 3 else 25)
    tm.encoder_size = 38000 if v >= 4 else (34000 if v >= 3 else 24000)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    print(f"vs ref(911.3): {os.path.relpath(pth, WS)} enc_v{v} sc={sc} FINAL_PICK={final} n={n}",
          flush=True)

    mk = make_mcts_agent_factory(sc, oracle_free=True)
    t0 = time.time()
    w, l, d, e = ER.run_matchup(
        model, list(DECK), list(DECK), lambda _d: make_ref_agent(), n,
        agent_factory=lambda _m, my, _o: mk(model, my, my))
    played = max(1, w + l + d)
    wr = w / played
    z = (wr - 0.5) / ((0.25 / played) ** 0.5)
    print(f"\n  {w}-{l}-{d}  wr {wr:.3f}  z {z:+.2f}  err {e}  ({time.time()-t0:.0f}s)")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "sc": sc, "final": final, "n": n,
               "w": w, "l": l, "d": d, "err": e, "wr": wr, "z": z},
              open(os.path.join(HERE, "results", f"vs_ref_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
