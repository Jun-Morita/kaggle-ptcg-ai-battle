"""Is the search actually searching, or just confirming the policy head?

Motivation. Two measurements sit oddly together:
    no search -> sc16   0.825 (z=+5.81)   large
    sc16      -> sc32   0.450 (z=-0.89)   nothing
A search that saturates that fast is either (a) fixing a few obvious blunders and
then hitting a wall, or (b) barely deviating from the prior at all. Two constants
make (b) plausible: create_node uses exp(policy*10) as the prior, which is
extremely peaked (a 0.2 gap in tanh output is a 7.4x prior ratio), and selection
uses c = 0.4*sqrt(N), low for a PUCT-style term.

There is also a structural candidate for (a): determinize() -- the sampling of the
opponent's hidden hand/deck/prizes -- is called ONCE, before the loop, so every
simulation reasons inside a single guessed world. Deeper search in one fixed world
cannot resolve uncertainty that lives in the hidden state.

This measures how often the search actually changes the move, and where the moved-to
action sat in the prior's ranking.

Usage: ENC_V3=1 uv run python diag_search.py <model.pth> [games] [--sc 16]
"""
from __future__ import annotations
import json
import os
import sys
import time
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
STATS = Counter()
RANKS = Counter()
VISITS = []


def instrumented_agent(model, deck, sc):
    """Runs the real mcts_agent, then recomputes the raw prior for the same
    position and records where the search's pick sat in the prior's order."""
    def agent(obs_dict):
        oc = to_observation_class(obs_dict)
        cands = tm.enumerate_candidates(oc)
        if len(cands) <= 1:
            return cands[0] if cands else [0]
        sv_e = tm.get_encoder_input(oc, deck, None)
        sv_d = tm.get_decoder_input(oc, cands)
        _, policy = tm.eval_nn(sv_e, sv_d, model)
        order = sorted(range(len(cands)), key=lambda i: -policy[i])
        raw = cands[order[0]]
        pick, _ = tm.mcts_agent(obs_dict, deck, model, sc, opp_deck=deck)
        STATS["decisions"] += 1
        STATS["cands"] += len(cands)
        if pick == raw:
            STATS["same"] += 1
            RANKS[0] += 1
        else:
            STATS["changed"] += 1
            r = next((k for k, i in enumerate(order) if cands[i] == pick), -1)
            RANKS[r] += 1
        # prior mass on the top choice: how peaked exp(policy*10) actually is
        import math
        ps = [math.exp(policy[i] * 10.0) for i in range(len(cands))]
        s = sum(ps)
        VISITS.append(max(ps) / s)
        return pick
    return agent


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 8)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16

    cfg = dict(LEGACY)
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    cfg.update({k: v for k, v in json.load(open(cand)).items() if k in cfg})
    deck = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    print(f"diag: {os.path.relpath(pth, WS)} {cfg} sc={sc} games={games}", flush=True)

    ag = instrumented_agent(model, deck, sc)
    t0 = time.time()
    for g in range(games):
        obs, _ = battle_start(list(deck), list(deck))
        while obs["current"]["result"] < 0:
            obs = battle_select(ag(obs))
        battle_finish()
        print(f"  game {g+1}/{games}  decisions={STATS['decisions']}"
              f"  changed={STATS['changed']}", flush=True)

    d = max(1, STATS["decisions"])
    print(f"\ndecisions {d}   mean candidates {STATS['cands']/d:.2f}")
    print(f"search CHANGED the move: {STATS['changed']}/{d} = {STATS['changed']/d:.3f}")
    print("prior rank of the chosen move (0 = the policy's own top pick):")
    for r in sorted(RANKS):
        print(f"   rank {r if r >= 0 else '?'}: {RANKS[r]:5d}  ({RANKS[r]/d:.3f})")
    VISITS.sort()
    print(f"prior mass on top choice: median {VISITS[len(VISITS)//2]:.3f}  "
          f"p10 {VISITS[len(VISITS)//10]:.3f}  p90 {VISITS[9*len(VISITS)//10]:.3f}")
    print(f"({time.time()-t0:.0f}s)")
    json.dump({"model": pth, "sc": sc, "games": games, "stats": dict(STATS),
               "ranks": dict(RANKS)},
              open(os.path.join(HERE, "results", f"diag_search_sc{sc}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
