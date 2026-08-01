"""A/B one search setting against the shipped one. Same net, same deck, both seats.

Generalises sweep_search.py (which only moved temp/c) to the two structural knobs
added in exp083l: DET_COUNT (how many hidden worlds the budget is split over) and
VALUE_SCALE (leaf evaluation on/off).

The question this exists to answer. Three measurements sit oddly together:

    no search -> sc16     0.825 (z=+5.81)    large
    sc16      -> sc32     0.450 (z=-0.89)    nothing
    loosening the prior   0.438..0.563       nothing (5 cells, exp083l)

A search that gains a lot at 16 sims, gains nothing at 32, and gets no better when
allowed to deviate from its prior is not a search that is reasoning about positions.
The held-out value AUC says the same thing from the training side:

    q1 0.639   q2 0.731   q3 0.838   q4 0.950     (sc083_d28s, n_val 200,444)

i.e. the value head is close to a coin flip in the first quarter of the game --
exactly where the search is supposed to earn its keep. If that is true, most of the
+0.325 is the tree finding forced results inside the horizon (terminal nodes are
exact), not the net judging quiet positions.

VALUE_SCALE=0 separates them: terminals keep their exact +1/0/-1, non-terminal
leaves return 0. If that plays about the same as the shipped agent, the value head
is contributing ~nothing and IS the bottleneck -- which also explains why loosening
the prior did not help (deviating from a good prior on the advice of a coin flip).

Usage: ENC_V3=1 uv run python ab_search.py <model.pth> [n] --vscale 0
                                                          --det 4
                                                          --temp 2.0 --c 2.0
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
KNOBS = ("SEARCH_TEMP", "PUCT_C", "DET_COUNT", "VALUE_SCALE", "FINAL_PICK")
BASE = {"SEARCH_TEMP": 10.0, "PUCT_C": 0.4, "DET_COUNT": 1, "VALUE_SCALE": 1.0,
        "FINAL_PICK": "visit"}


@contextlib.contextmanager
def settings(cfg):
    old = {k: getattr(tm, k) for k in KNOBS}
    for k, v in cfg.items():
        setattr(tm, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(tm, k, v)


def make(model, deck, sc, cfg):
    mk = make_mcts_agent_factory(sc, oracle_free=True)

    def agent(obs_dict):
        with settings(cfg):
            return mk(model, deck, deck)(obs_dict)
    return agent


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 80)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    cand = dict(BASE)
    for flag, key, cast in (("--temp", "SEARCH_TEMP", float), ("--c", "PUCT_C", float),
                            ("--det", "DET_COUNT", int), ("--vscale", "VALUE_SCALE", float),
                            ("--final", "FINAL_PICK", str)):
        if flag in sys.argv:
            cand[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    changed = {k: v for k, v in cand.items() if v != BASE[k]}
    if not changed:
        sys.exit("nothing to A/B: pass at least one of --temp/--c/--det/--vscale/--final")

    cfg = dict(LEGACY)
    arch = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    cfg.update({k: v for k, v in json.load(open(arch)).items() if k in cfg})
    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    tag = "_".join(f"{k.lower()}{v:g}" if isinstance(v, (int, float)) else f"{k.lower()}{v}"
                   for k, v in sorted(changed.items()))
    print(f"ab: {os.path.relpath(pth, WS)} sc={sc} n={n}\n  cand {changed}  vs base",
          flush=True)

    t0 = time.time()
    w, l, d, e = ER.run_matchup(
        model, deck, deck,
        lambda dk: make(model, dk, sc, BASE), n,
        agent_factory=lambda _m, my, _o: make(model, my, sc, cand))
    played = max(1, w + l + d)
    wr = w / played
    z = (wr - 0.5) / ((0.25 / played) ** 0.5)
    verdict = "PASS" if wr >= 0.57 else ("FLAT" if wr > 0.43 else "WORSE")
    print(f"\n  {w}-{l}-{d}  wr {wr:.3f}  z {z:+.2f}  err {e}  {verdict}  "
          f"({time.time()-t0:.0f}s)", flush=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "sc": sc, "n": n, "base": BASE, "cand": cand,
               "w": w, "l": l, "d": d, "err": e, "wr": wr, "z": z,
               "verdict": verdict},
              open(os.path.join(HERE, "results", f"ab_{tag}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
