"""Sweep the two constants that decide whether the search searches.

diag_search.py measured, over 1,059 real decisions with the shipped settings
(SEARCH_TEMP=10, PUCT_C=0.4):

    median prior mass on the top move   0.985
    search changed the move             14.6%  (9.4% of it to the prior's 2nd)

exp(policy*10) on a tanh head stretches the prior over a 20-logit range, so a
0.5 gap in policy output is a 148x prior ratio and c*prior/(1+visit) is ~0 for
every alternative. That is consistent with the other odd pair of measurements:
no-search -> sc16 was +0.325 but sc16 -> sc32 was nothing. A search that only
deviates on 1 decision in 7 saturates immediately.

Same net, same deck, seats alternated, search settings the only difference.

Usage: ENC_V3=1 uv run python sweep_search.py <model.pth> [n] --temp 3.0 --c 1.2
       (omit --temp/--c to sweep a small preset grid)
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
BASE = (10.0, 0.4)          # the shipped settings
GRID = [(3.0, 0.4), (3.0, 1.2), (5.0, 1.2), (10.0, 1.2), (2.0, 2.0)]


@contextlib.contextmanager
def search_params(temp, c):
    old = (tm.SEARCH_TEMP, tm.PUCT_C)
    tm.SEARCH_TEMP, tm.PUCT_C = temp, c
    try:
        yield
    finally:
        tm.SEARCH_TEMP, tm.PUCT_C = old


def make(model, deck, sc, temp, c):
    mk = make_mcts_agent_factory(sc, oracle_free=True)

    def agent(obs_dict):
        with search_params(temp, c):
            return mk(model, deck, deck)(obs_dict)
    return agent


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 80)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    if "--temp" in sys.argv or "--c" in sys.argv:
        t = float(sys.argv[sys.argv.index("--temp") + 1]) if "--temp" in sys.argv else BASE[0]
        cc = float(sys.argv[sys.argv.index("--c") + 1]) if "--c" in sys.argv else BASE[1]
        grid = [(t, cc)]
    else:
        grid = GRID

    cfg = dict(LEGACY)
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    cfg.update({k: v for k, v in json.load(open(cand)).items() if k in cfg})
    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    print(f"sweep: {os.path.relpath(pth, WS)} sc={sc} n={n} "
          f"base=(temp {BASE[0]}, c {BASE[1]})\n", flush=True)

    out = []
    for temp, c in grid:
        t0 = time.time()
        w, l, d, e = ER.run_matchup(
            model, deck, deck,
            lambda dk: make(model, dk, sc, *BASE), n,
            agent_factory=lambda _m, my, _o: make(model, my, sc, temp, c))
        played = max(1, w + l + d)
        wr = w / played
        z = (wr - 0.5) / ((0.25 / played) ** 0.5)
        tag = "PASS" if wr >= 0.57 else ("FLAT" if wr > 0.43 else "WORSE")
        print(f"  temp {temp:4.1f}  c {c:3.1f}   {w}-{l}-{d}  wr {wr:.3f}  "
              f"z {z:+.2f}  err {e}  {tag}  ({time.time()-t0:.0f}s)", flush=True)
        out.append({"temp": temp, "c": c, "w": w, "l": l, "d": d, "err": e,
                    "wr": wr, "z": z})
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "sc": sc, "n": n, "base": BASE, "results": out},
              open(os.path.join(HERE, "results", f"sweep_search_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
