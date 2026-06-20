"""exp010 Phase 3: belief-MCTS RL targeted at the LUCARIO-EX MIRROR.

Why re-target (vs Phase 2 which was an honest negative):
  - 2026-06-20 meta analysis: the field rotated back to ex-beatdown; the
    Lucario-ex MIRROR is ~57% of our opponents and v003 LOSES it (0.31-0.47).
  - The mirror is the ideal RL target: winnable (symmetric, skill decides),
    highest value (majority of field), and belief determinization is EXACT
    (we know the opponent's deck == our deck), so exp008's "belief makes search
    useful" holds in its best case. Beating Crustle with an all-ex line is a
    sparse/hard problem (needs the Hariyama pivot); the mirror is dense.

Stability fixes over Phase 2 (which collapsed: loss fell but eval went to 0):
  1. FIXED opponent = stock lucario_v2 policy (the field proxy), not a moving
     self-play target -> stable, grounded value labels.
  2. EXPERIENCE REPLAY: train on a buffer of the last K generations.
  3. CHECKPOINT GATING / anti-collapse: keep the best-eval net; if a generation
     regresses past a margin, revert to best before continuing.

Success metric: net (belief-MCTS) beats stock lucario_v2 in the mirror > 0.55
(v003 ref ~0.47). If so it is a genuine improvement over our submitted agent.

Usage: uv run python rl_phase3_mirror.py --generations 12 --search-count 24 \
         --games 28 --eval 16 --replay-gens 3 --warmstart results/bc_v003_multi.pth
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
import time
from collections import deque

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ["../exp001_harness", "../exp002_baselines", "../exp004_mcts", "../exp006_bc",
          "../exp007_anti_crustle", "../exp008_belief"]:
    ap = os.path.abspath(os.path.join(HERE, p))
    if ap not in sys.path:
        sys.path.insert(0, ap)

from harness import load_engine  # noqa
api, _ = load_engine()
import train_mcts as T  # noqa
import anti_crustle as AC  # noqa
from rl_phase2 import mcts_agent_belief  # reuse the belief-MCTS agent  # noqa
from cg.game import battle_start, battle_select, battle_finish  # noqa

RESULTS = os.path.join(HERE, "results")
LUCARIO = AC.LUCARIO_DECK


def make_stock_lucario():
    """The field proxy: stock lucario_v2 policy on the Lucario deck."""
    return AC.make_agent(LUCARIO)


def play_mirror(model, search_count, rng):
    """Net (belief-MCTS, Lucario) vs stock lucario_v2 (Lucario). Collect net samples.
    Belief is EXACT here: opp_deck == LUCARIO."""
    opp = make_stock_lucario()
    net_first = rng.random() < 0.5
    deck0, deck1 = (LUCARIO, LUCARIO)
    obs, sd = battle_start(deck0, deck1)
    if sd.errorPlayer >= 0:
        return [], None
    net_idx = 0 if net_first else 1
    samples = []
    while obs["current"]["result"] < 0:
        pi = obs["current"]["yourIndex"]
        if pi == net_idx:
            sel, s = mcts_agent_belief(obs, LUCARIO, LUCARIO, model, search_count, rng)
            if s is not None:
                samples.append(s)
        else:
            sel = opp(obs)
        obs = battle_select(sel)
    r = obs["current"]["result"]
    battle_finish()
    won = (r == net_idx)
    # TD(lambda) value labeling from the net's perspective
    LAMBDA = 0.9
    value = 1.0 if won else (0.0 if r == 2 else -1.0)
    for s in reversed(samples):
        label = (value + s.value) * 0.5
        value = value * LAMBDA + s.value * (1.0 - LAMBDA)
        s.value = label
    return samples, won


def evaluate_mirror(model, search_count, n, rng):
    """Win rate of net (belief-MCTS) vs stock lucario_v2 in the mirror."""
    opp = make_stock_lucario()
    w = d = 0
    for i in range(n):
        net_first = (i % 2 == 0)
        obs, sd = battle_start(LUCARIO, LUCARIO)
        if sd.errorPlayer >= 0:
            continue
        ni = 0 if net_first else 1
        while obs["current"]["result"] < 0:
            pi = obs["current"]["yourIndex"]
            if pi == ni:
                sel, _ = mcts_agent_belief(obs, LUCARIO, LUCARIO, model, search_count, rng)
            else:
                sel = opp(obs)
            obs = battle_select(sel)
        r = obs["current"]["result"]
        if r == ni:
            w += 1
        elif r == 2:
            d += 1
        battle_finish()
    return round(w / max(n, 1), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=12)
    ap.add_argument("--search-count", type=int, default=24)
    ap.add_argument("--games", type=int, default=28)
    ap.add_argument("--eval", type=int, default=16)
    ap.add_argument("--replay-gens", type=int, default=3)
    ap.add_argument("--revert-margin", type=float, default=0.12)
    ap.add_argument("--warmstart", default=os.path.join(RESULTS, "bc_v003_multi.pth"))
    ap.add_argument("--seed", type=int, default=44)
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    if os.path.exists(args.warmstart):
        model.load_state_dict(torch.load(args.warmstart, map_location=device))
        print(f"warm-started from {os.path.basename(args.warmstart)}", flush=True)
    else:
        print("WARNING: no warm-start; random init", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    os.makedirs(RESULTS, exist_ok=True)

    replay = deque(maxlen=args.replay_gens)
    best_wr, best_state = -1.0, None
    hist = []
    for gen in range(args.generations):
        t0 = time.perf_counter()
        # --- eval (anti-collapse gating) ---
        model.eval()
        with torch.inference_mode():
            wr = evaluate_mirror(model, args.search_count, args.eval, rng)
        gate = ""
        if wr > best_wr:
            best_wr, best_state = wr, copy.deepcopy(model.state_dict())
            torch.save(best_state, os.path.join(RESULTS, "rl3_best.pth"))
            gate = "  <- new best (saved rl3_best.pth)"
        elif best_state is not None and wr < best_wr - args.revert_margin:
            model.load_state_dict(best_state)
            gate = f"  <- regressed (wr {wr} < best {best_wr}); reverted to best"
        # --- collect self-play vs stock (belief-MCTS) ---
        with torch.inference_mode():
            new_samples, wld = [], [0, 0]
            for _ in range(args.games):
                s, won = play_mirror(model, args.search_count, rng)
                new_samples.extend(s)
                if won is not None:
                    wld[0 if won else 1] += 1
        replay.append(new_samples)
        train_set = [s for gens in replay for s in gens]
        print(f"[gen {gen}] mirror eval(vs stock)={wr} best={best_wr} | selfplay W-L={wld} "
              f"samples={len(new_samples)} replay={len(train_set)}{gate}", flush=True)
        # --- train on replay buffer ---
        model.train()
        loss = T.train(model, opt, train_set, device) if train_set else 0.0
        torch.save(model.state_dict(), os.path.join(RESULTS, "rl3_latest.pth"))
        dt = time.perf_counter() - t0
        print(f"[gen {gen}] loss={loss:.4f} {dt:.0f}s", flush=True)
        hist.append({"gen": gen, "eval_mirror": wr, "best": best_wr, "selfplay_WL": wld,
                     "loss": round(loss, 4), "sec": round(dt, 1)})
        json.dump({"args": vars(args), "history": hist},
                  open(os.path.join(RESULTS, "rl_phase3_history.json"), "w"), indent=2)
    print(f"done. best mirror winrate vs stock = {best_wr} (v003 ref ~0.47) -> rl3_best.pth")


if __name__ == "__main__":
    main()
