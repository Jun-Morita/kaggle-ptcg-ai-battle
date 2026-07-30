"""Is sc16 the right search budget, or just the one we happened to ship?

v045 ships SEARCH_COUNT=16 as an UPPER bound with an adaptive controller under it.
Its real ladder games consumed a median of 293.6s of the 600s budget (p90 482.5s,
max 505.9s) -- so roughly half the allowance goes unused, and the throttle almost
never engages. Meanwhile the measured search curve on the teacher was monotone
(sc4 0.517 / sc8 0.583 / sc16 0.733), which says nothing about where it flattens.

This pits MCTS(scA) against MCTS(scB) with the SAME net and the SAME deck on both
seats, so the search budget is the only difference -- no net, deck or pilot confound.

Usage: ENC_V3=1 uv run python sc_ladder.py <model.pth> [n] --a 32 --b 16
"""
from __future__ import annotations
import json
import os
import sys
import time

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
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 80)
    sa = int(sys.argv[sys.argv.index("--a") + 1]) if "--a" in sys.argv else 32
    sb = int(sys.argv[sys.argv.index("--b") + 1]) if "--b" in sys.argv else 16

    cfg = dict(LEGACY)
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    cfg.update({k: v for k, v in json.load(open(cand)).items() if k in cfg})
    assert tm.ENC_V3 == (1 if json.load(open(cand)).get("enc_version", 1) >= 3 else 0), \
        "ENC_V3 env does not match the checkpoint's enc_version -- features would differ"

    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()

    hi = make_mcts_agent_factory(sa, oracle_free=True)
    lo_f = make_mcts_agent_factory(sb, oracle_free=True)
    lo = lambda d: lo_f(model, d, d)  # noqa: E731
    print(f"SC LADDER  net={os.path.relpath(pth, WS)} {cfg} ENC_V3={tm.ENC_V3}\n"
          f"MCTS(sc={sa}) vs MCTS(sc={sb}), self-mirror Grimmsnarl, n={n}\n", flush=True)

    t0 = time.time()
    w, l, d, e = ER.run_matchup(model, deck, deck, lo, n, agent_factory=hi)
    played = w + l + d
    wr = w / played if played else 0.0
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"sc{sa} vs sc{sb}: {w}-{l}-{d}  errors={e}  sc{sa}_winrate={wr:.3f}  "
          f"z={z:+.2f}  ({time.time()-t0:.0f}s)")
    print("VERDICT:", f"more search still pays -- raise the cap above {sb}" if wr >= 0.55
          else (f"FLAT -- sc{sb} is already on the plateau, do not spend budget"
                if wr >= 0.45 else f"sc{sa} is WORSE than sc{sb}"))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "n": n, "sc_hi": sa, "sc_lo": sb, "w": w, "l": l, "d": d,
               "err": e, "hi_wr": wr, "z": z, "arch": cfg},
              open(os.path.join(HERE, "results", f"sc{sa}_vs_sc{sb}_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
