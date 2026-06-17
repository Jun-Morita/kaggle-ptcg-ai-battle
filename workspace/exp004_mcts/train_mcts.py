"""AlphaZero-style self-play training for the PTCG agent (exp004).

Adapted from the organizers' official "Reinforcement Learning and MCTS" sample
notebook (references/raw/official_notebooks/). The neural model, sparse feature
encoding and MCTS-over-Search-API logic follow the sample (verified by the
organizers); we parameterize the training loop, wire it to our local engine
(exp001) and decks (exp002), and add evaluation against the exp002 baseline pool.

Usage:
  uv run python train_mcts.py --generations 3 --search-count 16 \
      --selfplay 60 --eval 20 --deck lucario_v2
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
import torch.nn
import torch.nn.functional
import torch.optim

EXP1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa: E402

api, game = load_engine()
from cg.api import (  # noqa: E402
    AreaType, Card, Observation, PlayerState, Pokemon, SearchState, SelectContext,
    all_attack, all_card_data, search_begin, search_end, search_step, to_observation_class,
)
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# ---- card tables / sizes -------------------------------------------------------
all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}
card_count = max(all_card, key=lambda c: c.cardId).cardId + 1
attack_count = max(all_attack(), key=lambda a: a.attackId).attackId + 1

num_words_encoder = 24
encoder_size = 22000
decoder_main_feature = 8
decoder_attack_offset = 14
decoder_card_offset = decoder_attack_offset + attack_count
decoder_size = decoder_card_offset + (1 + decoder_main_feature + SelectContext.RECOVER_SPECIAL_CONDITION) * card_count


# ---- model ---------------------------------------------------------------------
class DecoderLayer(torch.nn.Module):
    def __init__(self, d_model, num_heads, d_feedforward):
        super().__init__()
        self.attention = torch.nn.MultiheadAttention(d_model, num_heads)
        self.fc1 = torch.nn.Linear(d_model, d_feedforward)
        self.fc2 = torch.nn.Linear(d_feedforward, d_model)
        self.norm1 = torch.nn.LayerNorm(d_model)
        self.norm2 = torch.nn.LayerNorm(d_model)

    def forward(self, x, encoder_out):
        y, _ = self.attention(x, encoder_out, encoder_out, need_weights=False)
        res = self.norm1(x + y)
        y = self.fc1(res)
        y = torch.nn.functional.relu(y)
        y = self.fc2(y)
        return self.norm2(res + y)


class MyModel(torch.nn.Module):
    def __init__(self, d_model, num_heads, d_feedforward, num_layers_encoder, num_layers_decoder):
        super().__init__()
        self.d_model = d_model
        self.encoder_bag = torch.nn.EmbeddingBag(encoder_size, d_model, mode="sum")
        encoder_layer = torch.nn.TransformerEncoderLayer(d_model, num_heads, d_feedforward, 0)
        self.encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers_encoder, enable_nested_tensor=False)
        self.encoder_fc = torch.nn.Linear(d_model, 1)
        self.decoder_bag = torch.nn.EmbeddingBag(decoder_size, d_model, mode="sum")
        self.decoder = torch.nn.ModuleList(
            [DecoderLayer(d_model, num_heads, d_feedforward) for _ in range(num_layers_decoder)]
        )
        self.decoder_fc = torch.nn.Linear(d_model, 1)

    def forward(self, ie, ve, oe, idx, vd, od):
        v = self.encoder_bag(ie, oe, ve)
        v = v.reshape(-1, num_words_encoder, self.d_model).transpose(0, 1)
        batch_size = v.size(1)
        encoder_out = self.encoder(v)
        v = self.encoder_fc(encoder_out)
        v = torch.tanh(v.mean(0))
        p = self.decoder_bag(idx, od, vd)
        p = p.reshape(batch_size, -1, self.d_model).transpose(0, 1)
        for layer in self.decoder:
            p = layer(p, encoder_out)
        p = self.decoder_fc(p)
        p = p.transpose(0, 1).view(batch_size, -1)
        p = torch.tanh(p)
        return (v, p)


# ---- sparse feature builders (verbatim logic from the sample) ------------------
class SparseVector:
    def __init__(self):
        self.index = []
        self.value = []
        self.offset = []
        self.pos = 0

    def add(self, index, value):
        value = float(value)
        if value != 0.0:
            self.index.append(self.pos + index)
            self.value.append(value)

    def add_pos(self, pos):
        self.pos += pos

    def add_single(self, value):
        value = float(value)
        if value != 0.0:
            self.index.append(self.pos)
            self.value.append(value)
        self.pos += 1

    def word_start(self):
        self.offset.append(len(self.index))


def add_card(sv, card):
    if card is not None:
        sv.add(card.id, 1)
    sv.add_pos(card_count)


def add_cards(sv, cards, value):
    if cards is not None:
        for card in cards:
            sv.add(card.id, value)
    sv.add_pos(card_count)


def add_pokemon(sv, poke):
    if poke is None:
        sv.add_single(1)
        sv.add_pos(1 + 3 * card_count)
    else:
        sv.add_single(0)
        sv.add_single(poke.hp / 400)
        add_card(sv, poke)
        add_cards(sv, poke.tools, 1.0)
        add_cards(sv, poke.energyCards, 0.5)


def add_player(sv, ps):
    sv.add_single(ps.deckCount / 60)
    sv.add_single(len(ps.discard) / 60)
    sv.add_single(ps.handCount / 8)
    sv.add_single(len(ps.bench) / 5)
    sv.add(len(ps.prize), 1)
    sv.add_pos(7)
    sv.add_single(ps.poisoned)
    sv.add_single(ps.burned)
    sv.add_single(ps.asleep)
    sv.add_single(ps.paralyzed)
    sv.add_single(ps.confused)
    add_cards(sv, ps.discard, 0.25)


def get_encoder_input(obs, your_deck):
    your_index = obs.current.yourIndex
    state = obs.current
    sv = SparseVector()
    for i in range(2):
        ps = state.players[i ^ your_index]
        for j in range(8):
            sv.word_start()
            pos = sv.pos
            if j < len(ps.bench):
                add_pokemon(sv, ps.bench[j])
            else:
                add_pokemon(sv, None)
            if j != 7:
                sv.pos = pos
    for i in range(2):
        ps = state.players[i ^ your_index]
        sv.word_start()
        if 0 < len(ps.active):
            add_pokemon(sv, ps.active[0])
        else:
            add_pokemon(sv, None)
    for i in range(2):
        ps = state.players[i ^ your_index]
        sv.word_start()
        add_player(sv, ps)
    sv.word_start()
    add_cards(sv, state.players[your_index].hand, 0.25)
    sv.word_start()
    for id in your_deck:
        sv.add(id, 0.25)
    sv.add_pos(card_count)
    sv.word_start()
    add_cards(sv, state.stadium, 1.0)
    sv.word_start()
    sv.add_single(1)
    sv.add_single(state.turn / 10)
    sv.add_single(state.firstPlayer == your_index)
    return sv


def get_card(obs, area, index, player_index):
    ps = obs.current.players[player_index]
    match area:
        case AreaType.DECK:
            return obs.select.deck[index]
        case AreaType.HAND:
            return ps.hand[index]
        case AreaType.DISCARD:
            return ps.discard[index]
        case AreaType.ACTIVE:
            return ps.active[index]
        case AreaType.BENCH:
            return ps.bench[index]
        case AreaType.PRIZE:
            return ps.prize[index]
        case AreaType.STADIUM:
            return obs.current.stadium[index]
        case AreaType.LOOKING:
            return obs.current.looking[index]
        case _:
            return None


def decoder_main(sv, feature_index, card):
    if card is not None:
        sv.add(decoder_card_offset + feature_index * card_count + card.id, 1)


def decoder_card_id(sv, context, card_id):
    sv.add(decoder_card_offset + (decoder_main_feature + context) * card_count + card_id, 1)


def decoder_card(sv, context, card):
    if card is not None:
        decoder_card_id(sv, context, card.id)


def get_decoder_input(obs, actions):
    from cg.api import OptionType
    sv = SparseVector()
    your_index = obs.current.yourIndex
    ps = obs.current.players[your_index]
    context = obs.select.context
    for action in actions:
        sv.word_start()
        if len(action) == 0:
            sv.add(0, 1)
            continue
        for i in action:
            o = obs.select.option[i]
            match o.type:
                case OptionType.END:
                    sv.add(1, 1)
                case OptionType.YES:
                    sv.add(2, 1)
                case OptionType.NO:
                    sv.add(3, 1)
                case OptionType.SPECIAL_CONDITION:
                    sv.add(4 + o.specialConditionType, 1)
                case OptionType.NUMBER:
                    sv.add(9 + min(o.number, 4), 1)
                case OptionType.ATTACK:
                    sv.add(decoder_attack_offset + o.attackId, 1)
                case OptionType.PLAY:
                    decoder_main(sv, 0, ps.hand[o.index])
                case OptionType.ATTACH:
                    decoder_main(sv, 1, get_card(obs, o.area, o.index, your_index))
                    decoder_main(sv, 2, get_card(obs, o.inPlayArea, o.inPlayIndex, your_index))
                case OptionType.EVOLVE:
                    decoder_main(sv, 3, get_card(obs, o.area, o.index, your_index))
                    decoder_main(sv, 4, get_card(obs, o.inPlayArea, o.inPlayIndex, your_index))
                case OptionType.ABILITY:
                    decoder_main(sv, 5, get_card(obs, o.area, o.index, your_index))
                case OptionType.DISCARD:
                    decoder_main(sv, 6, get_card(obs, o.area, o.index, your_index))
                case OptionType.RETREAT:
                    decoder_main(sv, 7, ps.active[0])
                case OptionType.CARD:
                    decoder_card(sv, context, get_card(obs, o.area, o.index, o.playerIndex))
                case OptionType.TOOL_CARD:
                    card = get_card(obs, o.area, o.index, o.playerIndex)
                    decoder_card(sv, context, card.tools[o.toolIndex])
                case OptionType.ENERGY_CARD | OptionType.ENERGY:
                    card = get_card(obs, o.area, o.index, o.playerIndex)
                    decoder_card(sv, context, card.energyCards[o.energyIndex])
                case OptionType.SKILL:
                    decoder_card_id(sv, context, o.cardId)
    return sv


def eval_nn(sv_enc, sv_dec, model):
    device = next(model.parameters()).device
    value, policy = model(
        torch.tensor(sv_enc.index, dtype=torch.int32, device=device),
        torch.tensor(sv_enc.value, dtype=torch.float32, device=device),
        torch.tensor(sv_enc.offset, dtype=torch.int32, device=device),
        torch.tensor(sv_dec.index, dtype=torch.int32, device=device),
        torch.tensor(sv_dec.value, dtype=torch.float32, device=device),
        torch.tensor(sv_dec.offset, dtype=torch.int32, device=device))
    return (value.tolist()[0][0], policy.tolist()[0])


# ---- MCTS ----------------------------------------------------------------------
class LearnSample:
    def __init__(self, value, policy, sv_enc, sv_dec):
        self.value = value
        self.policy = policy
        self.sv_enc = sv_enc
        self.sv_dec = sv_dec


class Child:
    def __init__(self, select, prob):
        self.node = None
        self.select = select
        self.prob = prob


class Node:
    def __init__(self, parent, state):
        self.value = -2.0
        self.total = 0.0
        self.visit = 0
        self.parent = parent
        self.children = []
        self.state = state

    def backprop(self, value):
        self.total += value
        self.visit += 1
        if self.parent is not None:
            self.parent.backprop(value)


def create_node(parent, search_state, your_index, your_deck, model):
    node = Node(parent, search_state)
    obs = search_state.observation
    state = obs.current
    if state.result >= 0:
        if state.result == 2:
            node.value = 0
        elif state.result == your_index:
            node.value = 1
        else:
            node.value = -1
        node.backprop(node.value)
        sample = None
    else:
        actions = []
        indices = list(range(obs.select.maxCount))
        for _ in range(64):
            actions.append(indices.copy())
            for i in range(len(indices)):
                index = len(indices) - i - 1
                if indices[index] < len(obs.select.option) - i - 1:
                    indices[index] += 1
                    for j in range(index + 1, len(indices)):
                        indices[j] = indices[j - 1] + 1
                    break
            else:
                break
        sv_enc = get_encoder_input(obs, your_deck)
        sv_dec = get_decoder_input(obs, actions)
        value, policy = eval_nn(sv_enc, sv_dec, model)
        v = value
        if state.yourIndex != your_index:
            v = -v
        node.value = v
        node.backprop(v)
        s = 0.0
        for i in range(len(policy)):
            p = math.exp(policy[i] * 10.0)
            node.children.append(Child(actions[i], p))
            s += p
        for c in node.children:
            c.prob /= s
        sample = LearnSample(value, policy, sv_enc, sv_dec)
    return (node, sample)


def mcts_agent(obs_dict, your_deck, model, search_count):
    obs = to_observation_class(obs_dict)
    your_index = obs.current.yourIndex
    state = obs.current
    active = state.players[1 - your_index].active
    search_state = search_begin(
        obs,
        your_deck=random.sample(your_deck, state.players[your_index].deckCount),
        your_prize=random.sample(your_deck, len(state.players[your_index].prize)),
        opponent_deck=[1072] * state.players[1 - your_index].deckCount,
        opponent_prize=[1] * len(state.players[1 - your_index].prize),
        opponent_hand=[1] * state.players[1 - your_index].handCount,
        opponent_active=[1072] if len(active) > 0 and active[0] is None else [])
    root, sample = create_node(None, search_state, your_index, your_deck, model)

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
                ss = search_step(current.state.searchId, nxt.select)
                nxt.node, _ = create_node(current, ss, your_index, your_deck, model)
                break
            else:
                current = nxt.node
                if current.state.observation.current.result >= 0:
                    current.backprop(current.value)
                    break

    max_child, max_visit, min_value = None, -1, 10
    for child in root.children:
        if child.node is not None:
            if max_visit < child.node.visit:
                max_child = child
                max_visit = child.node.visit
            v = child.node.total / child.node.visit
            if min_value > v:
                min_value = v

    if sample is not None:
        sample.value = root.total / root.visit
        for i in range(len(root.children)):
            child = root.children[i]
            v = sample.value
            if child.node is None:
                v = min_value - v - 0.03
            else:
                v = child.node.total / child.node.visit - v
            sample.policy[i] = max(-1.0, min(1.0, v))

    search_end()
    if max_child is None:  # fallback: no expanded child
        return (root.children[0].select if root.children else [0], sample)
    return (max_child.select, sample)


class LearnInput:
    def __init__(self):
        self.index = []
        self.value = []
        self.offset = []

    def add(self, sv):
        count = len(self.index)
        self.index.extend(sv.index)
        self.value.extend(sv.value)
        for o in sv.offset:
            self.offset.append(o + count)


def random_agent(obs_dict):
    obs = to_observation_class(obs_dict)
    return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)


# ---- training driver -----------------------------------------------------------
def load_deck(name):
    with open(os.path.join(EXP2, "policies", "decks.json")) as f:
        return json.load(f)[name]


def evaluate_vs_random(deck, model, search_count, n_games):
    results = [0, 0, 0]
    for i in range(n_games):
        obs, sd = battle_start(deck, deck)
        if sd.errorPlayer >= 0:
            raise ValueError(f"deck error type {sd.errorType}")
        your_index = i % 2
        while obs["current"]["result"] < 0:
            if obs["current"]["yourIndex"] == your_index:
                selected, _ = mcts_agent(obs, deck, model, search_count)
            else:
                selected = random_agent(obs)
            obs = battle_select(selected)
        battle_finish()
        r = obs["current"]["result"]
        results[2 if r == 2 else (0 if r == your_index else 1)] += 1
    return results


def selfplay(deck, model, search_count, n_games):
    sample_list = []
    for _ in range(n_games):
        obs, _ = battle_start(deck, deck)
        samples = [[], []]
        while obs["current"]["result"] < 0:
            selected, sample = mcts_agent(obs, deck, model, search_count)
            if sample is not None:
                samples[obs["current"]["yourIndex"]].append(sample)
            obs = battle_select(selected)
        battle_finish()
        for i in range(2):
            LAMBDA = 0.9
            value = 1.0 if i == obs["current"]["result"] else -1.0
            for sample in reversed(samples[i]):
                label = (value + sample.value) * 0.5
                value = value * LAMBDA + sample.value * (1.0 - LAMBDA)
                sample.value = label
                sample_list.append(sample)
    return sample_list


def train(model, optimizer, sample_list, device, batch_size=128):
    loss_fn_enc = torch.nn.HuberLoss(delta=0.2)
    loss_fn_dec = torch.nn.HuberLoss(reduction="none", delta=0.1)
    random.shuffle(sample_list)
    n_batches = len(sample_list) // batch_size
    total = 0.0
    for b in range(n_batches):
        ie, idd = LearnInput(), LearnInput()
        mask, le, ld = [], [], []
        for j in range(batch_size * b, batch_size * b + batch_size):
            s = sample_list[j]
            ie.add(s.sv_enc)
            idd.add(s.sv_dec)
            le.append(s.value)
            ld.extend(s.policy)
            for _ in range(len(s.policy)):
                mask.append(1.0)
            for _ in range(64 - len(s.policy)):
                mask.append(0.0)
                ld.append(0.0)
                idd.offset.append(len(idd.index))
        mt = torch.tensor(mask, dtype=torch.float32, device=device).view(batch_size, -1)
        lte = torch.tensor(le, dtype=torch.float32, device=device).view(batch_size, -1)
        ltd = torch.tensor(ld, dtype=torch.float32, device=device).view(batch_size, -1)
        optimizer.zero_grad()
        oe, od = model(
            torch.tensor(ie.index, dtype=torch.int32, device=device),
            torch.tensor(ie.value, dtype=torch.float32, device=device),
            torch.tensor(ie.offset, dtype=torch.int32, device=device),
            torch.tensor(idd.index, dtype=torch.int32, device=device),
            torch.tensor(idd.value, dtype=torch.float32, device=device),
            torch.tensor(idd.offset, dtype=torch.int32, device=device))
        loss_enc = loss_fn_enc(oe, lte)
        loss_dec = (loss_fn_dec(od, ltd) * mt).sum() / float(batch_size)
        loss = loss_enc + loss_dec
        loss.backward()
        optimizer.step()
        total += loss.item()
    return total / max(n_batches, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--search-count", type=int, default=16)
    ap.add_argument("--selfplay", type=int, default=60)
    ap.add_argument("--eval", type=int, default=20)
    ap.add_argument("--deck", default="lucario_v2")
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} card_count={card_count} attack_count={attack_count} "
          f"decoder_size={decoder_size}")

    deck = load_deck(args.deck)
    model = MyModel(args.d_model, 2, args.d_model * 2, 1, 1).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    history = []
    for gen in range(args.generations):
        t0 = time.perf_counter()
        model.eval()
        with torch.inference_mode():
            res = evaluate_vs_random(deck, model, args.search_count, args.eval)
            wr = 100 * res[0] // max(res[0] + res[1], 1)
            print(f"[gen {gen}] eval vs random: {res[0]}W-{res[1]}L-{res[2]}D ({wr}%)", flush=True)
            samples = selfplay(deck, model, args.search_count, args.selfplay)
        model.train()
        loss = train(model, optimizer, samples, device)
        dt = time.perf_counter() - t0
        torch.save(model.state_dict(), os.path.join(RESULTS_DIR, f"model_gen{gen}.pth"))
        print(f"[gen {gen}] samples={len(samples)} loss={loss:.4f} {dt:.0f}s", flush=True)
        history.append({"gen": gen, "winrate_vs_random": wr, "samples": len(samples),
                        "loss": round(loss, 4), "sec": round(dt, 1)})

    with open(os.path.join(RESULTS_DIR, "train_history.json"), "w") as f:
        json.dump({"args": vars(args), "history": history}, f, indent=2)
    print("done. saved models + train_history.json")


if __name__ == "__main__":
    main()
