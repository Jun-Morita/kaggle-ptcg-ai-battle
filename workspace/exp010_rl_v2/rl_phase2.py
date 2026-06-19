"""exp010 Phase 2: belief-MCTS RL fine-tuning of the BC warm-start net.

Differences from exp004 (which failed at 0.03):
  1. WARM-START from the Phase-1 BC net (not random).
  2. belief-grounded determinization (sample the opponent from a real meta
     decklist, not placeholder Snorlax) — exp008's key finding.
  3. The net plays its deck (Lucario) vs a META opponent pool (Crustle control
     weighted) with MCTS; samples get TD value from the game result -> policy
     iteration toward beating the meta.

Designed to run in the background and checkpoint every generation.

Usage: uv run python rl_phase2.py --generations 8 --search-count 16 --games 30
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ["../exp001_harness", "../exp002_baselines", "../exp004_mcts", "../exp006_bc",
          "../exp007_anti_crustle", "../exp008_belief"]:
    ap = os.path.abspath(os.path.join(HERE, p))
    if ap not in sys.path:
        sys.path.insert(0, ap)

from harness import load_engine  # noqa
api, _ = load_engine()
import train_mcts as T  # exp004: model, features, create_node, train, search_*  # noqa
import baselines as B  # noqa
import anti_crustle as AC  # noqa
from belief import belief_determinize  # exp008  # noqa
from cg.game import battle_start, battle_select, battle_finish  # noqa

RESULTS = os.path.join(HERE, "results")
LUCARIO = AC.LUCARIO_DECK
CRUSTLE = AC.CRUSTLE_DECK

# meta opponent pool (deck, rule-based-agent factory, sampling weight)
def _opp_pool():
    return [
        ("crustle", CRUSTLE, AC.make_crustle_agent, 3),
        ("lucario_v2", LUCARIO, lambda: B.make_policy_agent("lucario_v2"), 1),
        ("dragapult", B.DECKS["dragapult"], lambda: B.make_policy_agent("dragapult"), 1),
    ]


def mcts_agent_belief(obs_dict, my_deck, opp_deck, model, search_count, rng):
    """Like T.mcts_agent but with belief determinization (opp = real opp_deck)."""
    obs = T.to_observation_class(obs_dict)
    your_index = obs.current.yourIndex
    det = belief_determinize(obs, my_deck, opp_deck, rng)
    search_state = T.search_begin(obs, **det)
    root, sample = T.create_node(None, search_state, your_index, my_deck, model)
    for _ in range(search_count):
        current = root
        while True:
            value = -1e9
            c = 0.4 * math.sqrt(current.visit)
            nxt = None
            for child in current.children:
                visit = 0
                if child.node is None:
                    v = current.total / current.visit
                else:
                    v = child.node.total / child.node.visit
                    visit = child.node.visit
                if current.state.observation.current.yourIndex != your_index:
                    v = -v
                v += c * child.prob / (1 + visit)
                if value < v:
                    value = v
                    nxt = child
            if nxt is None:
                break
            if nxt.node is None:
                ss = T.search_step(current.state.searchId, nxt.select)
                nxt.node, _ = T.create_node(current, ss, your_index, my_deck, model)
                break
            current = nxt.node
            if current.state.observation.current.result >= 0:
                current.backprop(current.value)
                break
    max_child, max_visit, min_value = None, -1, 10
    for child in root.children:
        if child.node is not None:
            if max_visit < child.node.visit:
                max_child, max_visit = child, child.node.visit
            v = child.node.total / child.node.visit
            min_value = min(min_value, v)
    if sample is not None:
        sample.value = root.total / root.visit
        for i in range(len(root.children)):
            ch = root.children[i]
            v = sample.value
            v = (min_value - v - 0.03) if ch.node is None else (ch.node.total / ch.node.visit - v)
            sample.policy[i] = max(-1.0, min(1.0, v))
    T.search_end()
    if max_child is None:
        return (root.children[0].select if root.children else [0], sample)
    return (max_child.select, sample)


def play_and_collect(model, search_count, rng):
    """Net (Lucario deck, belief-MCTS) vs a sampled meta opponent. Collect net samples."""
    pool = _opp_pool()
    weights = [w for *_, w in pool]
    name, opp_deck, mk, _ = random.choices(pool, weights=weights, k=1)[0]
    opp = mk()
    net_first = rng.random() < 0.5
    deck0, deck1 = (LUCARIO, opp_deck) if net_first else (opp_deck, LUCARIO)
    obs, sd = battle_start(deck0, deck1)
    if sd.errorPlayer >= 0:
        return [], name, None
    net_idx = 0 if net_first else 1
    samples = []
    while obs["current"]["result"] < 0:
        pi = obs["current"]["yourIndex"]
        if pi == net_idx:
            sel, s = mcts_agent_belief(obs, LUCARIO, opp_deck, model, search_count, rng)
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
    return samples, name, won


def evaluate(model, search_count, n, rng):
    """Win rate vs Crustle and vs lucario_v2 (belief-MCTS)."""
    out = {}
    for name, odeck, mk, _w in _opp_pool():
        if name not in ("crustle", "lucario_v2"):
            continue
        w = 0
        for i in range(n):
            opp = mk()
            net_first = (i % 2 == 0)
            d0, d1 = (LUCARIO, odeck) if net_first else (odeck, LUCARIO)
            obs, sd = battle_start(d0, d1)
            if sd.errorPlayer >= 0:
                battle_finish() if False else None
                continue
            ni = 0 if net_first else 1
            while obs["current"]["result"] < 0:
                pi = obs["current"]["yourIndex"]
                if pi == ni:
                    sel, _ = mcts_agent_belief(obs, LUCARIO, odeck, model, search_count, rng)
                else:
                    sel = opp(obs)
                obs = battle_select(sel)
            if obs["current"]["result"] == ni:
                w += 1
            battle_finish()
        out[name] = round(w / n, 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=8)
    ap.add_argument("--search-count", type=int, default=16)
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--eval", type=int, default=10)
    ap.add_argument("--warmstart", default=os.path.join(RESULTS, "bc_v003_multi.pth"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    if os.path.exists(args.warmstart):
        model.load_state_dict(torch.load(args.warmstart, map_location=device))
        print(f"warm-started from {os.path.basename(args.warmstart)}", flush=True)
    else:
        print("WARNING: no warm-start found, random init", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    os.makedirs(RESULTS, exist_ok=True)

    hist = []
    for gen in range(args.generations):
        t0 = time.perf_counter()
        model.eval()
        with torch.inference_mode():
            ev = evaluate(model, args.search_count, args.eval, rng)
            samples = []
            rec = {"crustle": [0, 0]}
            for _ in range(args.games):
                s, name, won = play_and_collect(model, args.search_count, rng)
                samples.extend(s)
                if name == "crustle" and won is not None:
                    rec["crustle"][0 if won else 1] += 1
        print(f"[gen {gen}] eval vs {ev} | selfplay crustle W-L={rec['crustle']} "
              f"samples={len(samples)}", flush=True)
        model.train()
        loss = T.train(model, opt, samples, device) if samples else 0.0
        torch.save(model.state_dict(), os.path.join(RESULTS, f"rl_gen{gen}.pth"))
        torch.save(model.state_dict(), os.path.join(RESULTS, "rl_latest.pth"))
        dt = time.perf_counter() - t0
        print(f"[gen {gen}] loss={loss:.4f} {dt:.0f}s", flush=True)
        hist.append({"gen": gen, "eval": ev, "loss": round(loss, 4), "sec": round(dt, 1)})
        json.dump({"args": vars(args), "history": hist},
                  open(os.path.join(RESULTS, "rl_phase2_history.json"), "w"), indent=2)
    print("done -> rl_latest.pth")


if __name__ == "__main__":
    main()
