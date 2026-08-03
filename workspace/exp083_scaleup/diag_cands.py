"""How much of the legal move space does enumerate_candidates() never offer?

Two restrictions are visible in the code, both inherited verbatim from the
official sample (train_mcts.enumerate_candidates):

  indices = list(range(obs.select.maxCount))   # always EXACTLY maxCount picks
  for _ in range(64):                          # and at most 64 of them

The engine's rule is minCount <= len(selection) <= maxCount, so wherever
minCount < maxCount the agent cannot express "take fewer" at all -- every
"discard up to N" / "search for up to N" / "bench up to N" decision is forced to
the maximum. The 64 cap truncates in ascending index order, so when the true
combination count exceeds 64 the tail of the option list is unreachable.

Neither shows up in any metric we have: the moves are legal, nothing crashes, and
the policy head is only ever trained on candidates from this same generator, so
the BC labels agree with it by construction. This is the same shape of defect as
the visit-tie bug -- found by reading, not by measuring.

Counts both, by SelectContext, over real self-play decisions.

Usage: ENC_V3=1 uv run python diag_cands.py <model.pth> [games]
"""
from __future__ import annotations
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
TOT = Counter()
BY_CTX = {}


def note(obs):
    sel = obs.select
    n, lo, hi = len(sel.option), sel.minCount, sel.maxCount
    ctx = getattr(sel, "context", None)
    ctx = int(ctx) if ctx is not None else -1
    row = BY_CTX.setdefault(ctx, Counter())
    TOT["decisions"] += 1
    row["decisions"] += 1
    if hi > lo:
        TOT["variable_size"] += 1
        row["variable_size"] += 1
        # how many legal selections exist that we never enumerate
        missed = sum(math.comb(n, k) for k in range(lo, hi))
        row["missed_sizes"] += (hi - lo)
        TOT["missed_total"] += min(missed, 10 ** 6)
    full = math.comb(n, hi) if hi <= n else 0
    if full > 64:
        TOT["truncated"] += 1
        row["truncated"] += 1
    if n > 1:
        TOT["multi_option"] += 1


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 20)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    cfg = dict(LEGACY)
    cfg.update({k: v for k, v in json.load(
        open(os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json"))).items()
        if k in cfg})
    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    print(f"diag_cands: {os.path.relpath(pth, WS)} sc={sc} games={games}", flush=True)

    for g in range(games):
        obs, _ = battle_start(list(deck), list(deck))
        while obs["current"]["result"] < 0:
            oc = to_observation_class(obs)
            if oc.select is not None and oc.select.option:
                note(oc)
            sel, _ = tm.mcts_agent(obs, deck, model, sc, opp_deck=deck)
            obs = battle_select(sel)
        battle_finish()
        print(f"  game {g+1}/{games}  decisions={TOT['decisions']}", flush=True)

    d = max(1, TOT["decisions"])
    print(f"\ndecisions {d}")
    print(f"  minCount < maxCount (we CANNOT take fewer): {TOT['variable_size']} "
          f"= {TOT['variable_size']/d:.3f}")
    print(f"  combinations > 64 (tail unreachable):       {TOT['truncated']} "
          f"= {TOT['truncated']/d:.3f}")
    print("\nby SelectContext (context: decisions, variable-size, truncated):")
    for ctx, row in sorted(BY_CTX.items(), key=lambda kv: -kv[1]["decisions"]):
        if row["variable_size"] or row["truncated"]:
            print(f"  ctx {ctx:>3}: {row['decisions']:5d}  var {row['variable_size']:5d}"
                  f"  trunc {row['truncated']:5d}")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "games": games, "total": dict(TOT),
               "by_ctx": {str(k): dict(v) for k, v in BY_CTX.items()}},
              open(os.path.join(HERE, "results", "diag_cands.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
