"""How much of the search's uncertainty is a coin flip it sampled once and reused?

search_begin(..., manual_coin=False) lets the engine resolve coin flips with its
own RNG. That is right for a stochastic game -- but the tree is persistent: a node
is created by ONE search_step call, and every later simulation that descends
through it reuses that SearchState, i.e. that one coin outcome. The tree therefore
has no chance nodes; each branch is frozen to the first flip it happened to draw.
Same shape as determinize() being called once (exp083l), which measured FLAT.

Before building anything, measure whether it can matter at all:
  (a) how many of our decisions occur in a turn that contains a coin flip
  (b) how many log entries per game are flips, and how lopsided they are

LogType is read from obs.logs, which ENC_V3 does not encode (ENC_V4 added a heads/
tails count word -- and ENC_V4 measured FLAT twice, which is weak evidence that
coin information is not where the value is).

Usage: ENC_V3=1 uv run python diag_coin.py <model.pth> [games]
"""
from __future__ import annotations
import json
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
from cg.api import to_observation_class, LogType  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
TOT = Counter()
LOGKIND = Counter()


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 20)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    coin_types = {n: getattr(LogType, n) for n in dir(LogType)
                  if "COIN" in n.upper() or "FLIP" in n.upper()}
    print(f"coin-ish LogTypes: {coin_types}", flush=True)

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

    for g in range(games):
        obs, _ = battle_start(list(deck), list(deck))
        while obs["current"]["result"] < 0:
            oc = to_observation_class(obs)
            if oc.select is not None and oc.select.option:
                TOT["decisions"] += 1
                logs = getattr(oc, "logs", None) or []
                n_coin = 0
                for lg in logs:
                    LOGKIND[int(lg.type)] += 1
                    if int(lg.type) in set(coin_types.values()):
                        n_coin += 1
                if n_coin:
                    TOT["decisions_with_coin_in_turn"] += 1
                    TOT["coin_events"] += n_coin
            sel, _ = tm.mcts_agent(obs, deck, model, sc, opp_deck=deck)
            obs = battle_select(sel)
        battle_finish()
        print(f"  game {g+1}/{games}  decisions={TOT['decisions']}  "
              f"with-coin={TOT['decisions_with_coin_in_turn']}", flush=True)

    d = max(1, TOT["decisions"])
    print(f"\ndecisions {d} over {games} games")
    print(f"  decisions whose visible log contains a coin flip: "
          f"{TOT['decisions_with_coin_in_turn']} = {TOT['decisions_with_coin_in_turn']/d:.3f}")
    print(f"  coin events seen (with repeats across decisions): {TOT['coin_events']}")
    print("\nLogType histogram (top 12):")
    names = {int(getattr(LogType, n)): n for n in dir(LogType) if not n.startswith("_")
             and isinstance(getattr(LogType, n), int)}
    for t, c in LOGKIND.most_common(12):
        print(f"  {names.get(t, t):<28} {c}")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "games": games, "total": dict(TOT),
               "logkind": {str(k): v for k, v in LOGKIND.items()}},
              open(os.path.join(HERE, "results", "diag_coin.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
