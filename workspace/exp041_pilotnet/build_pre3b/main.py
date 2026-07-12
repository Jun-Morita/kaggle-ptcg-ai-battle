"""exp041 ship-path trial -- self-contained, torch-free MCTS agent for a real
submission bundle (main.py). Validation scope ONLY (per user: build + smoke
test locally, do NOT submit to Kaggle): proves the numpy-ported net (npnet.py,
parity-verified against torch) + exp040's MCTS/determinization logic can run
end-to-end inside the crash-safe submission sandbox with zero torch dependency.

Opponent-deck handling under real-ladder uncertainty (updated for pre2):
- ENCODER feature: opp_deck word fed as None (oracle-free). pre2 was trained
  with p=0.3 dropout of this word; measured oracle-free accuracy (0.829) ==
  oracle accuracy (0.830), and the n=50 oracle-free field eval matches the
  oracle one -- this is the ship-correct condition, not a compromise.
- DETERMINIZATION (hidden-card sampling for search_begin): still needs SOME
  60-card list for the opponent; my_deck is used as the fallback (mirror
  assumption). Imperfect for non-mirror matchups; archetype detection
  (exp038/039) is the known upgrade path.

Everything below is self-contained (no imports from workspace/exp040_mctsv2 or
exp041_pilotnet -- the submission sandbox only has main.py + deck.csv + cg/ +
weights_pure.pkl, no access to this repo's other directories) so it can be
packaged verbatim into a tar by build_np_submission.py.

NUMPY-FREE (2026-07-09, fixes v015's "Validation Episode failed" crash): none
of our 14 prior shipped submissions ever used numpy, and cg's own source has
zero numpy imports -- the "cg depends on numpy so it's available in the
sandbox" assumption behind the original npnet.py was never actually verified
and is refuted by that crash. This file's forward pass and weight loading are
now pure stdlib (math + array + pickle), no numpy import anywhere.
"""
from __future__ import annotations
import array
import math
import os
import pickle
import random
from collections import Counter

from cg.api import (
    AreaType, CardType, OptionType, SelectContext,
    all_card_data, search_begin, search_end, search_step, to_observation_class,
)

SEARCH_COUNT = 0  # raw argmax; sc16 MCTS = ~2.3s/act, too slow for the sandbox per-act budget
NUM_WORDS_ENCODER = 25
D = 128
H = 2
HD = D // H

all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}
POKEMON_IDS = {c.cardId for c in all_card if c.cardType == CardType.POKEMON}
card_count = max(all_card, key=lambda c: c.cardId).cardId + 1
attack_count = 0
try:
    from cg.api import all_attack
    attack_count = max(all_attack(), key=lambda a: a.attackId).attackId + 1
except Exception:
    attack_count = 400  # generous fallback; only affects decoder feature layout size
decoder_main_feature = 8
decoder_attack_offset = 14
decoder_card_offset = decoder_attack_offset + attack_count
decoder_size = decoder_card_offset + (1 + decoder_main_feature + SelectContext.RECOVER_SPECIAL_CONDITION) * card_count


# ---- deck ------------------------------------------------------------------------
def read_deck_csv():
    fp = "deck.csv"
    if not os.path.exists(fp):
        fp = "/kaggle_simulations/agent/deck.csv"
    with open(fp) as f:
        return [int(line) for line in f.read().strip().split("\n")]


my_deck = read_deck_csv()


# ---- pure-python net (numpy-free port; see exp041_pilotnet/npnet.py for the
# original numpy port + its torch parity test: max err 1.3e-5, argmax 500/500.
# This file reimplements the same math with math/array/lists only, verified
# against the numpy version by export_pure.py's companion parity check.) -----
def _vec(n, val=0.0):
    return [val] * n


def _linear(x, W, b, out_dim, in_dim):
    """x: list[in_dim]. W: flat array.array, row-major (out_dim, in_dim). b: array/list[out_dim]."""
    y = [0.0] * out_dim
    for o in range(out_dim):
        base = o * in_dim
        s = b[o]
        for i in range(in_dim):
            s += x[i] * W[base + i]
        y[o] = s
    return y


def _mat_linear(xs, W, b, out_dim, in_dim):
    return [_linear(x, W, b, out_dim, in_dim) for x in xs]


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


def _relu(x):
    return [v if v > 0.0 else 0.0 for v in x]


def _layer_norm(x, g, b, eps=1e-5):
    n = len(x)
    m = sum(x) / n
    v = sum((xi - m) ** 2 for xi in x) / n
    inv = 1.0 / math.sqrt(v + eps)
    return [(xi - m) * inv * g[i] + b[i] for i, xi in enumerate(x)]


def _softmax(x):
    m = max(x)
    ex = [math.exp(v - m) for v in x]
    s = sum(ex)
    return [v / s for v in ex]


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _mha(q_in, kv_in, ipw, ipb, opw, opb):
    """q_in: list[Sq][D], kv_in: list[Sk][D]. ipw/ipb: in_proj (3D,D)/(3D,).
    opw/opb: out_proj (D,D)/(D,)."""
    Sq, Sk = len(q_in), len(kv_in)
    wq, bq = ipw[:D * D], ipb[:D]
    wk, bk = ipw[D * D:2 * D * D], ipb[D:2 * D]
    wv, bv = ipw[2 * D * D:3 * D * D], ipb[2 * D:3 * D]
    q = _mat_linear(q_in, wq, bq, D, D)
    k = _mat_linear(kv_in, wk, bk, D, D)
    v = _mat_linear(kv_in, wv, bv, D, D)
    scale = 1.0 / math.sqrt(HD)
    out = [[0.0] * D for _ in range(Sq)]
    for h in range(H):
        lo, hi = h * HD, (h + 1) * HD
        for si in range(Sq):
            qh = q[si][lo:hi]
            scores = [_dot(qh, k[sj][lo:hi]) * scale for sj in range(Sk)]
            a = _softmax(scores)
            acc = [0.0] * HD
            for sj in range(Sk):
                aw = a[sj]
                vh = v[sj][lo:hi]
                for d in range(HD):
                    acc[d] += aw * vh[d]
            out[si][lo:hi] = acc
    return _mat_linear(out, opw, opb, D, D)


def _emb_bag(weight, idx, val, off, n_bags):
    """weight: flat array.array, row-major (vocab, D)."""
    ends = list(off[1:]) + [len(idx)]
    out = []
    for b in range(n_bags):
        s, e = off[b], ends[b]
        acc = [0.0] * D
        for j in range(s, e):
            base = idx[j] * D
            vj = val[j]
            for d in range(D):
                acc[d] += weight[base + d] * vj
        out.append(acc)
    return out


class NpNet:
    """Pure-stdlib (no numpy). Weight file = pickle of {name: (shape, array.array('f', flat))}."""

    def __init__(self, pkl_path):
        with open(pkl_path, "rb") as f:
            raw = pickle.load(f)
        self.w = {k: v for k, (_shape, v) in raw.items()}

    def forward(self, ie, ve, oe, idx, vd, od):
        w = self.w
        n_enc = len(oe)
        x = _emb_bag(w["encoder_bag.weight"], ie, ve, oe, n_enc)
        y = _mha(x, x, w["encoder.layers.0.self_attn.in_proj_weight"],
                 w["encoder.layers.0.self_attn.in_proj_bias"],
                 w["encoder.layers.0.self_attn.out_proj.weight"],
                 w["encoder.layers.0.self_attn.out_proj.bias"])
        x = [_layer_norm(_add(xi, yi), w["encoder.layers.0.norm1.weight"],
                          w["encoder.layers.0.norm1.bias"]) for xi, yi in zip(x, y)]
        y = _mat_linear(x, w["encoder.layers.0.linear1.weight"], w["encoder.layers.0.linear1.bias"], 256, D)
        y = [_relu(yi) for yi in y]
        y = _mat_linear(y, w["encoder.layers.0.linear2.weight"], w["encoder.layers.0.linear2.bias"], D, 256)
        enc = [_layer_norm(_add(xi, yi), w["encoder.layers.0.norm2.weight"],
                            w["encoder.layers.0.norm2.bias"]) for xi, yi in zip(x, y)]
        vlogits = _mat_linear(enc, w["encoder_fc.weight"], w["encoder_fc.bias"], 1, D)
        v = math.tanh(sum(row[0] for row in vlogits) / len(vlogits))

        n_dec = len(od)
        p = _emb_bag(w["decoder_bag.weight"], idx, vd, od, n_dec)
        y = _mha(p, enc, w["decoder.0.attention.in_proj_weight"],
                 w["decoder.0.attention.in_proj_bias"],
                 w["decoder.0.attention.out_proj.weight"],
                 w["decoder.0.attention.out_proj.bias"])
        p = [_layer_norm(_add(pi, yi), w["decoder.0.norm1.weight"],
                          w["decoder.0.norm1.bias"]) for pi, yi in zip(p, y)]
        y = _mat_linear(p, w["decoder.0.fc1.weight"], w["decoder.0.fc1.bias"], 256, D)
        y = [_relu(yi) for yi in y]
        y = _mat_linear(y, w["decoder.0.fc2.weight"], w["decoder.0.fc2.bias"], D, 256)
        p = [_layer_norm(_add(pi, yi), w["decoder.0.norm2.weight"],
                          w["decoder.0.norm2.bias"]) for pi, yi in zip(p, y)]
        plogits = _mat_linear(p, w["decoder_fc.weight"], w["decoder_fc.bias"], 1, D)
        policy = [math.tanh(row[0]) for row in plogits]
        return v, policy


# NOTE (root cause of v015/fix/fix2/fix3 all crashing): Kaggle's real harness
# loads main.py via kaggle_environments.agent.get_last_callable, which execs
# the source TEXT in a bare namespace -- __file__ is NEVER defined there. Our
# local sandbox_replica.py used importlib.spec_from_file_location instead,
# which DOES set __file__, so it never reproduced this crash (NameError:
# name '__file__' is not defined, raised at import, before agent() exists).
# Fix: locate weights the same relative-path way deck.csv already does
# (relative first, /kaggle_simulations/agent/ as the sandbox fallback) --
# never touch __file__.
_PKL_CANDIDATES = [
    "weights_pure.pkl",
    os.path.join("cg", "weights_pure.pkl"),
    "/kaggle_simulations/agent/weights_pure.pkl",
    "/kaggle_simulations/agent/cg/weights_pure.pkl",
]
# NEVER crash at import: a failed/missing weight load degrades to a legal
# fallback policy instead of failing the whole validation episode.
MODEL = None
for _pkl in _PKL_CANDIDATES:
    try:
        if os.path.exists(_pkl):
            MODEL = NpNet(_pkl)
            break
    except Exception:
        MODEL = None


# ---- sparse feature builders (verbatim logic from train_mcts.py, exp040) ----------
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


def get_encoder_input(obs, your_deck, opp_deck=None):
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
    for cid in your_deck:
        sv.add(cid, 0.25)
    sv.add_pos(card_count)
    sv.word_start()
    for cid in (opp_deck if opp_deck is not None else your_deck):
        sv.add(cid, 0.25)
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
    if area == AreaType.DECK:
        return obs.select.deck[index]
    if area == AreaType.HAND:
        return ps.hand[index]
    if area == AreaType.DISCARD:
        return ps.discard[index]
    if area == AreaType.ACTIVE:
        return ps.active[index]
    if area == AreaType.BENCH:
        return ps.bench[index]
    if area == AreaType.PRIZE:
        return ps.prize[index]
    if area == AreaType.STADIUM:
        return obs.current.stadium[index]
    if area == AreaType.LOOKING:
        return obs.current.looking[index]
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
            t = o.type
            if t == OptionType.END:
                sv.add(1, 1)
            elif t == OptionType.YES:
                sv.add(2, 1)
            elif t == OptionType.NO:
                sv.add(3, 1)
            elif t == OptionType.SPECIAL_CONDITION:
                sv.add(4 + o.specialConditionType, 1)
            elif t == OptionType.NUMBER:
                sv.add(9 + min(o.number, 4), 1)
            elif t == OptionType.ATTACK:
                sv.add(decoder_attack_offset + o.attackId, 1)
            elif t == OptionType.PLAY:
                decoder_main(sv, 0, ps.hand[o.index])
            elif t == OptionType.ATTACH:
                decoder_main(sv, 1, get_card(obs, o.area, o.index, your_index))
                decoder_main(sv, 2, get_card(obs, o.inPlayArea, o.inPlayIndex, your_index))
            elif t == OptionType.EVOLVE:
                decoder_main(sv, 3, get_card(obs, o.area, o.index, your_index))
                decoder_main(sv, 4, get_card(obs, o.inPlayArea, o.inPlayIndex, your_index))
            elif t == OptionType.ABILITY:
                decoder_main(sv, 5, get_card(obs, o.area, o.index, your_index))
            elif t == OptionType.DISCARD:
                decoder_main(sv, 6, get_card(obs, o.area, o.index, your_index))
            elif t == OptionType.RETREAT:
                decoder_main(sv, 7, ps.active[0])
            elif t == OptionType.CARD:
                decoder_card(sv, context, get_card(obs, o.area, o.index, o.playerIndex))
            elif t == OptionType.TOOL_CARD:
                card = get_card(obs, o.area, o.index, o.playerIndex)
                decoder_card(sv, context, card.tools[o.toolIndex])
            elif t in (OptionType.ENERGY_CARD, OptionType.ENERGY):
                card = get_card(obs, o.area, o.index, o.playerIndex)
                decoder_card(sv, context, card.energyCards[o.energyIndex])
            elif t == OptionType.SKILL:
                decoder_card_id(sv, context, o.cardId)
    return sv


def enumerate_candidates(obs):
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
    return actions


def eval_nn(sv_enc, sv_dec, model):
    v, p = model.forward(sv_enc.index, sv_enc.value, sv_enc.offset,
                          sv_dec.index, sv_dec.value, sv_dec.offset)
    return v, list(p)


# ---- determinization (verbatim port of exp040/determinize.py) --------------------
def _card_ids(cards):
    out = []
    for c in cards or []:
        cid = getattr(c, "id", None)
        if cid is not None:
            out.append(cid)
    return out


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None))
        out += _card_ids(getattr(m, "tools", None))
    return out


def _extra_visible_cards(obs):
    state = obs.current
    out = list(state.stadium or [])
    sel = obs.select
    if sel is not None:
        eff = getattr(sel, "effect", None)
        if eff is not None:
            out.append(eff)
        ctx = getattr(sel, "contextCard", None)
        if ctx is not None:
            out.append(ctx)
    return out


def _visible_ids(player, include_hand, player_index, extra_cards):
    ids = _mon_ids(player.active) + _mon_ids(player.bench) + _card_ids(player.discard)
    if include_hand:
        ids += _card_ids(player.hand)
    counts = Counter(ids)
    for c in extra_cards:
        if getattr(c, "playerIndex", None) == player_index:
            counts[c.id] = max(counts[c.id], 1)
    return list(counts.elements())


def _sample_unseen_pool(deck, visible_ids, needed, rng):
    rem = Counter(deck)
    rem.subtract(Counter(visible_ids))
    pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
    if len(pool) < needed:
        pool = list(deck)
    rng.shuffle(pool)
    return pool


def determinize(obs, your_index, my_d, opp_d, pokemon_ids, rng=None):
    rng = rng or random
    state = obs.current
    extra_cards = _extra_visible_cards(obs)
    me = state.players[your_index]
    opp = state.players[1 - your_index]

    my_visible = _visible_ids(me, True, your_index, extra_cards)
    my_needed = me.deckCount + len(me.prize)
    my_pool = _sample_unseen_pool(my_d, my_visible, my_needed, rng)
    your_deck_s = my_pool[: me.deckCount]
    your_prize = my_pool[me.deckCount: me.deckCount + len(me.prize)]

    active = opp.active
    active_unknown = len(active) > 0 and active[0] is None
    opp_visible = _visible_ids(opp, False, 1 - your_index, extra_cards)
    opp_needed = opp.deckCount + len(opp.prize) + opp.handCount + (1 if active_unknown else 0)
    opp_pool = _sample_unseen_pool(opp_d, opp_visible, opp_needed, rng)

    opponent_active = []
    if active_unknown:
        for i, cid in enumerate(opp_pool):
            if cid in pokemon_ids:
                opponent_active = [opp_pool.pop(i)]
                break
        else:
            fallback = next((cid for cid in opp_d if cid in pokemon_ids), None)
            opponent_active = [fallback] if fallback is not None else []

    c = 0

    def take(k):
        nonlocal c
        out = opp_pool[c: c + k]
        c += k
        return out

    opponent_deck = take(opp.deckCount)
    opponent_prize = take(len(opp.prize))
    opponent_hand = take(opp.handCount)

    return dict(your_deck=your_deck_s, your_prize=your_prize,
                opponent_deck=opponent_deck, opponent_prize=opponent_prize,
                opponent_hand=opponent_hand, opponent_active=opponent_active)


# ---- MCTS (verbatim port of exp040/train_mcts.py, torch eval_nn -> numpy) ---------
class LearnSample:
    def __init__(self, value, policy, sv_enc, sv_dec):
        self.value = value
        self.policy = policy


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


def create_node(parent, search_state, your_index, your_deck, model, opp_deck=None):
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
    else:
        actions = enumerate_candidates(obs)
        # oracle-free encoder (pre2 trained with opp_deck-word dropout); the
        # opp_deck arg is only used by determinize() for hidden-card sampling
        sv_enc = get_encoder_input(obs, your_deck, None)
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
    return node


def raw_agent(obs_dict, your_deck, model):
    """Single-forward argmax (no engine search). ~0.15s/act locally vs the
    ~2.3s/act of MCTS sc16, which drained the sandbox per-act time budget and
    caused v015-fix's "Validation Episode failed" (every successful prior
    submission acts in milliseconds). Raw and MCTS16 measured equal on the
    n=50 field eval (2.16 vs 2.14), so the strength cost is ~nil."""
    obs = to_observation_class(obs_dict)
    actions = enumerate_candidates(obs)
    sv_enc = get_encoder_input(obs, your_deck, None)
    sv_dec = get_decoder_input(obs, actions)
    _v, policy = eval_nn(sv_enc, sv_dec, model)
    best = max(range(len(actions)), key=lambda i: policy[i])
    return actions[best]


def mcts_agent(obs_dict, your_deck, model, search_count, opp_deck=None):
    if search_count <= 0:
        return raw_agent(obs_dict, your_deck, model)
    obs = to_observation_class(obs_dict)
    your_index = obs.current.yourIndex
    search_state = search_begin(
        obs, **determinize(obs, your_index, your_deck,
                            your_deck if opp_deck is None else opp_deck, POKEMON_IDS))
    root = create_node(None, search_state, your_index, your_deck, model, opp_deck)

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
                nxt.node = create_node(current, ss, your_index, your_deck, model, opp_deck)
                break
            else:
                current = nxt.node
                if current.state.observation.current.result >= 0:
                    current.backprop(current.value)
                    break

    max_child, max_visit = None, -1
    for child in root.children:
        if child.node is not None and max_visit < child.node.visit:
            max_child = child
            max_visit = child.node.visit

    search_end()
    if max_child is None:
        return root.children[0].select if root.children else [0]
    return max_child.select


# ---- crash-safe entrypoint ---------------------------------------------------------
def _legal_fallback(select):
    n = len(select.option)
    return [] if n == 0 else list(range(min(max(1, select.minCount), n)))


def _valid(sel, select):
    n = len(select.option)
    if not isinstance(sel, list) or any((not isinstance(i, int)) or i < 0 or i >= n for i in sel):
        return False
    if len(set(sel)) != len(sel):
        return False
    return select.minCount <= len(sel) <= select.maxCount


_SLOW_STRIKES = 0  # acts that exceeded the per-act budget; 3 strikes disables the net


def _tail_fallback(select):
    """Distinctive-but-legal fallback (LAST options, unlike _legal_fallback's
    FIRST) so ladder replays reveal that the net was disabled (weights missing
    or too slow) rather than crash-safety firing."""
    n = len(select.option)
    k = min(max(1, select.minCount), n)
    return list(range(n - k, n))


def agent(obs_dict):
    global MODEL, _SLOW_STRIKES
    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        return list(my_deck) if obs_dict.get("select") is None else [0]
    if obs.select is None:
        return list(my_deck)
    if not obs.select.option:
        return []
    if MODEL is None:
        return _tail_fallback(obs.select)
    try:
        import time as _time
        _t0 = _time.time()
        sel = mcts_agent(obs_dict, my_deck, MODEL, SEARCH_COUNT, opp_deck=my_deck)
        if _time.time() - _t0 > 1.5:  # sandbox act budget guard (v015-fix lesson)
            _SLOW_STRIKES += 1
            if _SLOW_STRIKES >= 3:
                MODEL = None  # permanently degrade to the fast fallback
        return sel if _valid(sel, obs.select) else _legal_fallback(obs.select)
    except Exception:
        try:
            return _legal_fallback(obs.select)
        except Exception:
            return random.sample(list(range(len(obs.select.option))), max(1, obs.select.minCount))
