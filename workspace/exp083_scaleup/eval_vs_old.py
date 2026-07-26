"""exp083 Stage-3 gate 2 -- does the SCALED net actually out-play the exp080 net?

Head-to-head on the SAME Grimmsnarl deck, both sides raw argmax, both oracle-free,
seats alternated. This is the least-biased local test we have: identical deck,
identical feature pipeline, same model family -- so it cannot repeat the dragapult
/ pub1034 failure mode, where the comparison was contaminated by a mismatched
opponent PILOT rather than the thing under test.

It is still a LOCAL number: passing it does not justify shipping (see
[[local-not-ladder]]). It is a necessary condition for spending a ladder slot.

Usage:
  uv run python eval_vs_old.py NEW.pth [--old OLD.pth] [--n 200]
Arch is read from the sibling arch.json of each checkpoint (legacy = d128/h2/1+1).
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

DEFAULT_OLD = os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm10", "model_ep2.pth")
DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")
LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}


def load_net(pth, device):
    """Rebuild the exact model from the checkpoint's sibling arch.json."""
    cfg = dict(LEGACY)
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    if os.path.exists(cand):
        cfg.update(json.load(open(cand)))
    cfg.setdefault("d_ff", cfg["d_model"] * 2)
    m = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                   cfg["enc_layers"], cfg["dec_layers"]).to(device)
    m.load_state_dict(torch.load(pth, map_location=device))
    m.eval()
    return m, cfg


def main():
    pths = [a for a in sys.argv[1:] if a.endswith(".pth")]
    new_path = pths[0]
    old_path = (sys.argv[sys.argv.index("--old") + 1] if "--old" in sys.argv
                else (pths[1] if len(pths) > 1 else DEFAULT_OLD))
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 200

    deck = json.load(open(DECK))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    new, ncfg = load_net(new_path, device)
    old, ocfg = load_net(old_path, device)

    print(f"NEW {os.path.relpath(new_path, WS)}  {ncfg}")
    print(f"OLD {os.path.relpath(old_path, WS)}  {ocfg}")
    print(f"self-mirror Grimmsnarl, raw argmax, oracle-free, n={n}\n", flush=True)

    new_factory = lambda _m, my, opp: ER.make_raw_agent(new, my, opp, oracle_free=True)  # noqa: E731
    old_opp = lambda d: ER.make_raw_agent(old, d, d, oracle_free=True)  # noqa: E731

    t0 = time.time()
    w, l, dr, e = ER.run_matchup(new, deck, deck, old_opp, n, agent_factory=new_factory)
    played = w + l + dr
    wr = w / played if played else 0.0
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"NEW vs OLD: {w}-{l}-{dr}  errors={e}  new_winrate={wr:.3f}  z={z:+.2f}  "
          f"({time.time()-t0:.0f}s)")
    print("VERDICT:", "PASS -- scaled net out-plays exp080's net (necessary, not sufficient)"
          if wr >= 0.55 else
          ("FLAT -- capacity bought nothing; do NOT spend a ladder slot" if wr >= 0.45
           else "NEGATIVE -- scaled net is WORSE; retire this config"))
    json.dump({"new": new_path, "old": old_path, "n": n, "w": w, "l": l, "d": dr,
               "errors": e, "new_winrate": wr, "z": z, "new_arch": ncfg},
              open(os.path.join(HERE, "results",
                                f"vs_old_{os.path.basename(os.path.dirname(new_path))}_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
