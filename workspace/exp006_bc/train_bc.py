"""Behavior cloning (exp006): imitate the strong rule-based lucario_v2 policy.

Generates (observation -> expert choice) data by letting lucario_v2 play (mirror
+ vs the exp002 pool for opponent diversity), then trains the exp004 network to
predict the expert's chosen action (policy, cross-entropy) and the game outcome
(value, Huber). The resulting net plays GREEDILY without search (fast), aiming to
approach the teacher's strength (~0.68 vs pool) and to warm-start MCTS later.

Reuses exp004's model + feature builders (train_mcts as T) and exp002 experts.

Usage:
  uv run python train_bc.py --games 150 --epochs 4
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import torch
import torch.nn.functional as F

HERE = os.path.dirname(__file__)
EXP1 = os.path.abspath(os.path.join(HERE, "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(HERE, "..", "exp002_baselines"))
EXP4 = os.path.abspath(os.path.join(HERE, "..", "exp004_mcts"))
for p in (EXP1, EXP2, EXP4):
    if p not in sys.path:
        sys.path.insert(0, p)

import train_mcts as T  # noqa: E402  (model + feature builders + engine)
from baselines import make_policy_agent, DECKS  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
MAX_ACTIONS = 64


def enumerate_actions(select):
    """Same candidate-combo enumeration as train_mcts.create_node."""
    actions = []
    indices = list(range(select.maxCount))
    for _ in range(MAX_ACTIONS):
        actions.append(indices.copy())
        for i in range(len(indices)):
            index = len(indices) - i - 1
            if indices[index] < len(select.option) - i - 1:
                indices[index] += 1
                for j in range(index + 1, len(indices)):
                    indices[j] = indices[j - 1] + 1
                break
        else:
            break
    return actions


class Sample:
    __slots__ = ("sv_enc", "sv_dec", "n_actions", "target", "player", "value")

    def __init__(self, sv_enc, sv_dec, n_actions, target, player):
        self.sv_enc = sv_enc
        self.sv_dec = sv_dec
        self.n_actions = n_actions
        self.target = target
        self.player = player
        self.value = 0.0


def record_game(expert0, expert1, deck0, deck1, record_players, samples):
    """Play one game; record (features, expert target) for players in record_players."""
    obs, sd = battle_start(deck0, deck1)
    if sd.errorPlayer >= 0:
        raise ValueError(f"deck error {sd.errorType}")
    experts = [expert0, expert1]
    decks = [deck0, deck1]
    game_samples = []
    while obs["current"]["result"] < 0:
        o = T.to_observation_class(obs)
        pi = o.current.yourIndex
        sel = experts[pi](obs)
        if pi in record_players and o.select is not None and o.select.maxCount >= 0:
            actions = enumerate_actions(o.select)
            key = sorted(sel)
            target = next((idx for idx, a in enumerate(actions) if a == key), None)
            if target is not None and len(actions) >= 2:
                sv_enc = T.get_encoder_input(o, decks[pi])
                sv_dec = T.get_decoder_input(o, actions)
                game_samples.append(Sample(sv_enc, sv_dec, len(actions), target, pi))
        obs = battle_select(sel)
    result = obs["current"]["result"]
    battle_finish()
    for s in game_samples:
        s.value = 0.0 if result == 2 else (1.0 if result == s.player else -1.0)
    samples.extend(game_samples)
    return result


def generate_data(deck_name, n_games, seed):
    random.seed(seed)
    deck = DECKS[deck_name]
    samples = []
    # mirror games (record both sides) — independent expert modules for shared globals
    mirror = max(1, n_games // 2)
    for _ in range(mirror):
        e0 = make_policy_agent(deck_name)
        e1 = make_policy_agent(deck_name)
        record_game(e0, e1, deck, deck, {0, 1}, samples)
    # vs-pool games (record only the expert side) for opponent diversity
    pool = ["dragapult", "lucario_v1", "abomasnow", "iono"]
    rest = n_games - mirror
    for g in range(rest):
        opp_name = pool[g % len(pool)]
        expert = make_policy_agent(deck_name)
        opp = make_policy_agent(opp_name)
        if g % 2 == 0:
            record_game(expert, opp, deck, DECKS[opp_name], {0}, samples)
        else:
            record_game(opp, expert, DECKS[opp_name], deck, {1}, samples)
    return samples


def build_batch(batch, device):
    ie, idd = T.LearnInput(), T.LearnInput()
    targets, values, masks = [], [], []
    for s in batch:
        ie.add(s.sv_enc)
        idd.add(s.sv_dec)
        targets.append(s.target)
        values.append(s.value)
        m = [0.0] * MAX_ACTIONS
        for k in range(s.n_actions):
            m[k] = 1.0
        masks.append(m)
        # pad decoder words to MAX_ACTIONS so policy output is [B, MAX_ACTIONS]
        for _ in range(MAX_ACTIONS - s.n_actions):
            idd.offset.append(len(idd.index))
    enc = (torch.tensor(ie.index, dtype=torch.int32, device=device),
           torch.tensor(ie.value, dtype=torch.float32, device=device),
           torch.tensor(ie.offset, dtype=torch.int32, device=device))
    dec = (torch.tensor(idd.index, dtype=torch.int32, device=device),
           torch.tensor(idd.value, dtype=torch.float32, device=device),
           torch.tensor(idd.offset, dtype=torch.int32, device=device))
    return (enc, dec,
            torch.tensor(targets, dtype=torch.long, device=device),
            torch.tensor(values, dtype=torch.float32, device=device).view(-1, 1),
            torch.tensor(masks, dtype=torch.float32, device=device))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=150)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--deck", default="lucario_v2")
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--value-weight", type=float, default=0.5)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}  generating BC data from {args.games} games ...", flush=True)
    t0 = time.perf_counter()
    samples = generate_data(args.deck, args.games, args.seed)
    print(f"collected {len(samples)} samples in {time.perf_counter()-t0:.0f}s", flush=True)

    model = T.MyModel(args.d_model, 2, args.d_model * 2, 1, 1).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    history = []
    for epoch in range(args.epochs):
        model.train()
        random.shuffle(samples)
        n_batches = max(1, len(samples) // args.batch)
        tot_p = tot_v = correct = seen = 0.0
        te = time.perf_counter()
        for b in range(n_batches):
            batch = samples[b * args.batch:(b + 1) * args.batch]
            if len(batch) < 2:
                continue
            enc, dec, target, value, mask = build_batch(batch, device)
            out_v, out_p = model(enc[0], enc[1], enc[2], dec[0], dec[1], dec[2])
            logits = out_p.masked_fill(mask == 0, -1e9)
            loss_p = F.cross_entropy(logits, target)
            loss_v = F.huber_loss(out_v, value, delta=0.5)
            loss = loss_p + args.value_weight * loss_v
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot_p += loss_p.item()
            tot_v += loss_v.item()
            correct += (logits.argmax(1) == target).sum().item()
            seen += len(batch)
        acc = correct / max(seen, 1)
        print(f"[epoch {epoch}] policy_loss={tot_p/n_batches:.4f} value_loss={tot_v/n_batches:.4f} "
              f"train_acc={acc:.3f} {time.perf_counter()-te:.0f}s", flush=True)
        history.append({"epoch": epoch, "policy_loss": round(tot_p / n_batches, 4),
                        "value_loss": round(tot_v / n_batches, 4), "imitation_acc": round(acc, 3)})
        torch.save(model.state_dict(), os.path.join(RESULTS_DIR, f"bc_model_e{epoch}.pth"))

    torch.save(model.state_dict(), os.path.join(RESULTS_DIR, "bc_model.pth"))
    with open(os.path.join(RESULTS_DIR, "bc_history.json"), "w") as f:
        json.dump({"args": vars(args), "n_samples": len(samples), "history": history}, f, indent=2)
    print("done. saved bc_model.pth + bc_history.json")


if __name__ == "__main__":
    main()
