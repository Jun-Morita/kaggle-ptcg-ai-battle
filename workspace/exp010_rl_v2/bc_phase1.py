"""exp010 Phase 1: multi-opponent behavior cloning of the v003 anti-Crustle policy.

Teacher = our best agent (v003 anti-Crustle, Lucario deck). We record the
teacher's decisions across a diverse opponent pool that INCLUDES the meta
(Crustle control), so the cloned net learns to play our best line against the
real field. Reuses exp006's model + feature builders (train_mcts via exp006).

The resulting greedy (no-search) net is a fast warm-start for Phase-2 RL.

Usage: uv run python bc_phase1.py --games 400 --epochs 20
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
import time

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
EXP1 = os.path.abspath(os.path.join(HERE, "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(HERE, "..", "exp002_baselines"))
EXP4 = os.path.abspath(os.path.join(HERE, "..", "exp004_mcts"))
EXP6 = os.path.abspath(os.path.join(HERE, "..", "exp006_bc"))
EXP7 = os.path.abspath(os.path.join(HERE, "..", "exp007_anti_crustle"))
for p in (EXP1, EXP2, EXP4, EXP6, EXP7):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402
api, _ = load_engine()
import train_mcts as T  # exp004: model + features  # noqa: E402
from train_bc import enumerate_actions, Sample, build_batch  # exp006  # noqa: E402
import baselines as B  # noqa: E402
import anti_crustle as AC  # exp007  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402

RESULTS = os.path.join(HERE, "results")
LUCARIO = AC.LUCARIO_DECK
CRUSTLE = AC.CRUSTLE_DECK


def make_v003(deck=LUCARIO):
    """v003 anti-Crustle patched policy (our best) playing `deck`."""
    POL = os.path.join(EXP7, "policy_anticrustle.py")
    spec = importlib.util.spec_from_file_location(f"v003_{random.randint(0,1<<30)}", POL)
    m = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(os.path.join(EXP2, "policies"))
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(m)
    finally:
        os.chdir(prev)

    def agent(obs_dict):
        o = T.to_observation_class(obs_dict)
        return list(deck) if o.select is None else m.agent(obs_dict)
    return agent


def record_game(teacher, teacher_deck, opp, opp_deck, record_player, samples):
    obs, sd = battle_start(teacher_deck if record_player == 0 else opp_deck,
                           opp_deck if record_player == 0 else teacher_deck)
    if sd.errorPlayer >= 0:
        return
    agents = [teacher, opp] if record_player == 0 else [opp, teacher]
    decks = [teacher_deck, opp_deck] if record_player == 0 else [opp_deck, teacher_deck]
    game = []
    while obs["current"]["result"] < 0:
        o = T.to_observation_class(obs)
        pi = o.current.yourIndex
        sel = agents[pi](obs)
        if pi == record_player and o.select is not None:
            actions = enumerate_actions(o.select)
            tgt = next((i for i, a in enumerate(actions) if a == sorted(sel)), None)
            if tgt is not None and len(actions) >= 2:
                game.append(Sample(T.get_encoder_input(o, decks[pi]),
                                   T.get_decoder_input(o, actions), len(actions), tgt, pi))
        obs = battle_select(sel)
    r = obs["current"]["result"]
    battle_finish()
    for s in game:
        s.value = 0.0 if r == 2 else (1.0 if r == s.player else -1.0)
    samples.extend(game)


def generate(n_games, seed):
    random.seed(seed)
    samples = []
    # opponent pool incl. the meta (Crustle control)
    pool = [("crustle", lambda: make_v003(CRUSTLE) if False else B_make_crustle(), CRUSTLE),
            ("lucario_v2", lambda: B.make_policy_agent("lucario_v2"), LUCARIO),
            ("dragapult", lambda: B.make_policy_agent("dragapult"), B.DECKS["dragapult"]),
            ("iono", lambda: B.make_policy_agent("iono"), B.DECKS["iono"])]
    per = max(1, n_games // (len(pool) + 1))
    for name, mk, odeck in pool:
        for g in range(per):
            teacher = make_v003(LUCARIO)
            record_game(teacher, LUCARIO, mk(), odeck, g % 2, samples)
    # mirror (teacher vs teacher), record both
    for g in range(per):
        record_game(make_v003(LUCARIO), LUCARIO, make_v003(LUCARIO), LUCARIO, g % 2, samples)
    return samples


def B_make_crustle():
    return AC.make_crustle_agent()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=400)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--value-weight", type=float, default=0.5)
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"device={device}; generating multi-opponent BC data ({args.games} games)...", flush=True)
    t0 = time.perf_counter()
    samples = generate(args.games, args.seed)
    print(f"collected {len(samples)} samples in {time.perf_counter()-t0:.0f}s", flush=True)

    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    os.makedirs(RESULTS, exist_ok=True)
    hist = []
    for ep in range(args.epochs):
        model.train(); random.shuffle(samples)
        nb = max(1, len(samples) // args.batch); tp = tv = corr = seen = 0.0
        for b in range(nb):
            batch = samples[b*args.batch:(b+1)*args.batch]
            if len(batch) < 2:
                continue
            enc, dec, target, value, mask = build_batch(batch, device)
            ov, op = model(enc[0], enc[1], enc[2], dec[0], dec[1], dec[2])
            logits = op.masked_fill(mask == 0, -1e9)
            lp = F.cross_entropy(logits, target); lv = F.huber_loss(ov, value, delta=0.5)
            loss = lp + args.value_weight * lv
            opt.zero_grad(); loss.backward(); opt.step()
            tp += lp.item(); tv += lv.item(); corr += (logits.argmax(1) == target).sum().item(); seen += len(batch)
        acc = corr / max(seen, 1)
        print(f"[ep {ep}] policy_loss={tp/nb:.4f} value_loss={tv/nb:.4f} imitation_acc={acc:.3f}", flush=True)
        hist.append({"epoch": ep, "acc": round(acc, 3)})
        torch.save(model.state_dict(), os.path.join(RESULTS, "bc_v003_multi.pth"))
    json.dump({"args": vars(args), "n_samples": len(samples), "history": hist},
              open(os.path.join(RESULTS, "bc_phase1_history.json"), "w"), indent=2)
    print("done -> bc_v003_multi.pth")


if __name__ == "__main__":
    main()
