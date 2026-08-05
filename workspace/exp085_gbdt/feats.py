"""Flat per-option feature rows for a gradient-boosted ranker.

Why this exists. Our transformer BC line has produced 16+ honest negatives: nets
that are indistinguishable from each other on every local gate we built and that
regress on the ladder (the 28-day corpus cost ~70 points while gate_field called
it FLAT). The public tetsutani agent reaches a comparable score with a completely
different learner -- ~1300 boosted trees over ~256 hand-named flat features,
scoring each legal OPTION independently and taking the top-k. That formulation is
far lower variance than a sequence model at this data scale, its inference is pure
Python (no numpy, ~180KB of weights), and, unlike an opaque embedding, every
feature has a name you can audit.

This module is our own feature design, written against the engine API we already
use (train_mcts's accessors). Nothing is copied from that notebook; the borrowed
idea is the SHAPE of the problem -- rank options with explicit features -- which
is the part that is actually load-bearing.

Two design points worth stating because we learned them the hard way:

  duplicate identity. exp042 found that comparing actions by option INDEX counts
  "same card, different copy" as a mismatch and inflated a measured diff by ~0.4.
  So each option carries dup_count / dup_rank: how many options are semantically
  identical to it, and which copy this one is. The model can then learn "any of
  the three Poffins" instead of memorising a position.

  recent history. A turn is a sequence, and a scorer that sees only the current
  observation cannot tell "I already searched this turn" from "I have not". Three
  previous chosen actions are folded in as flat fields.

Row layout is fixed by FEATURES (a list of names). build_rows.py and the pure
exporter both read that list, so adding a feature in one place is enough.
"""
from __future__ import annotations
import sys, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2"):
    if os.path.join(WS, p) not in sys.path:
        sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

from cg.api import AreaType, OptionType, all_attack, all_card_data  # noqa: E402

# The 60-card list is fixed for our submission, so per-card counters are a fixed
# width. Sorted unique ids of the Grimmsnarl deck.
DECK_IDS = [7, 104, 112, 646, 647, 648, 860, 1079, 1080, 1086, 1097, 1122, 1137,
            1152, 1182, 1219, 1227, 1231, 1259]
BENCH_SLOTS = 5
HAND_SLOTS = 20
N_OPT_TYPES = 16

_CD = None
_ATK = None


def _atk_table():
    """attackId -> (damage, energy_cost, owner_card_id).

    diag_errors.py on the first model found a coherent bias: ABILITY and EVOLVE
    options were promoted far more often than the teacher takes them (603/404)
    while ATTACK, RETREAT and END were dropped far more often (220/101/57). In
    other words the ranker keeps acting when the teacher would swing or stop.

    The likely reason is that nothing in the row said what an attack DOES -- only
    opt_attack_id, an opaque code the trees would have to memorise. This is the
    same shape as the Speed Up case in DeNA's Pokemon TCG Pocket writeup
    (invenglobal 24133), where the fix was not to penalise the action but to add
    the precondition the model could not see; correct usage went to 96.2%.
    """
    global _ATK
    if _ATK is None:
        # CardData.attacks holds attack IDs, not Attack objects; all_attack() is
        # the table. `damage` is already an int here, but a few entries in other
        # sets carry things like "60+", so parse defensively.
        _ATK = {}
        for a in all_attack():
            d = getattr(a, "damage", 0)
            if not isinstance(d, int):
                digits = "".join(ch for ch in str(d or "") if ch.isdigit())
                d = int(digits) if digits else 0
            _ATK[int(a.attackId)] = (int(d), len([e for e in (a.energies or []) if e]))
    return _ATK


def card_meta(cid):
    """(stage, cardType, retreatCost, hp, ex_rank) for a card id; 0s if unknown."""
    global _CD
    if _CD is None:
        _CD = {int(c.cardId): c for c in all_card_data()}
    c = _CD.get(int(cid or 0))
    if c is None:
        return (0, 0, 0, 0, 0)
    stage = 3 if c.stage2 else (2 if c.stage1 else (1 if c.basic else 0))
    ex = 3 if c.megaEx else (2 if c.ex else (1 if c.tera else 0))
    return (stage, int(c.cardType), int(c.retreatCost or 0), int(c.hp or 0), ex)


def _names():
    f = ["turn", "turn_action_count", "first_player", "energy_attached",
         "supporter_played", "stadium_played", "retreated", "context",
         "select_type", "min_count", "max_count", "n_options",
         "remain_damage", "remain_energy", "stadium_id", "context_card_id",
         "looking_n"]
    for side in ("own", "opp"):
        f += [f"{side}_deck", f"{side}_hand", f"{side}_discard", f"{side}_prize",
              f"{side}_bench_n", f"{side}_poisoned", f"{side}_burned",
              f"{side}_asleep", f"{side}_paralyzed", f"{side}_confused",
              f"{side}_total_hp", f"{side}_total_damage", f"{side}_total_energy"]
        for slot in ["active"] + [f"bench{i}" for i in range(BENCH_SLOTS)]:
            f += [f"{side}_{slot}_id", f"{side}_{slot}_hp", f"{side}_{slot}_maxhp",
                  f"{side}_{slot}_damage", f"{side}_{slot}_energy_n",
                  f"{side}_{slot}_tools", f"{side}_{slot}_appear",
                  f"{side}_{slot}_stage", f"{side}_{slot}_retreat"]
    for cid in DECK_IDS:
        f += [f"hand_c{cid}", f"discard_c{cid}", f"inplay_c{cid}"]
    f += [f"hand_pos{i}_id" for i in range(HAND_SLOTS)]
    f += [f"opt_type_count_{i}" for i in range(N_OPT_TYPES)]
    for k in (1, 2, 3):
        f += [f"prev{k}_type", f"prev{k}_source_id", f"prev{k}_target_id",
              f"prev{k}_attack_id", f"prev{k}_area"]
    # --- state-level answers to "is stopping / swinging / retreating right?" ---
    f += ["best_attack_damage", "lethal_available", "prize_diff",
          "n_attack_opts", "n_ability_opts", "n_evolve_opts", "n_play_opts",
          "n_end_opts", "n_retreat_opts",
          "own_active_retreat_cost", "own_active_retreat_payable",
          "own_active_hp_ratio", "opp_active_hp_ratio"]
    f += ["opt_pos", "opt_pos_norm", "opt_type", "opt_area", "opt_index",
          "opt_player_rel", "opt_inplay_area", "opt_inplay_index", "opt_attack_id",
          "opt_number", "opt_count", "opt_card_id",
          "src_id", "src_stage", "src_type", "src_retreat", "src_meta_hp", "src_ex",
          "tgt_id", "tgt_stage", "tgt_type", "tgt_retreat", "tgt_meta_hp", "tgt_ex",
          "tgt_cur_hp", "tgt_maxhp", "tgt_damage", "tgt_energy_n", "tgt_appear",
          "tgt_is_active", "tgt_is_own",
          "opt_attack_damage", "opt_attack_energy", "opt_attack_lethal",
          "opt_attack_margin",
          "dup_count", "dup_rank"]
    return f


FEATURES = _names()
IDX = {n: i for i, n in enumerate(FEATURES)}
N_FEATURES = len(FEATURES)
# Trees split on ordered values; ids and enum codes are categorical. LightGBM is
# told which is which so it does not read "card 1259 > card 7" as a magnitude.
CATEGORICAL = [n for n in FEATURES if n.endswith("_id") or n in (
    "context", "select_type", "opt_type", "opt_area", "opt_inplay_area",
    "src_type", "tgt_type", "prev1_area", "prev2_area", "prev3_area",
    "prev1_type", "prev2_type", "prev3_type")]


def _poke(row, base, p):
    if p is None:
        return
    st, _ct, rc, _hp, _ex = card_meta(p.id)
    row[base + 0] = float(p.id or 0)
    row[base + 1] = float(p.hp or 0)
    row[base + 2] = float(p.maxHp or 0)
    row[base + 3] = float((p.maxHp or 0) - (p.hp or 0))
    row[base + 4] = float(len(p.energyCards or []))
    row[base + 5] = float(len(p.tools or []))
    row[base + 6] = float(p.appearThisTurn or 0)
    row[base + 7] = float(st)
    row[base + 8] = float(rc)


def base_state(obs, history):
    """Everything that does not depend on which option we are scoring."""
    row = [0.0] * N_FEATURES
    st = obs.current
    yi = st.yourIndex
    sel = obs.select
    row[IDX["turn"]] = float(st.turn)
    row[IDX["turn_action_count"]] = float(st.turnActionCount)
    row[IDX["first_player"]] = float(st.firstPlayer == yi)
    row[IDX["energy_attached"]] = float(st.energyAttached)
    row[IDX["supporter_played"]] = float(st.supporterPlayed)
    row[IDX["stadium_played"]] = float(st.stadiumPlayed)
    row[IDX["retreated"]] = float(st.retreated)
    row[IDX["context"]] = float(getattr(sel, "context", -1) or -1)
    row[IDX["select_type"]] = float(getattr(sel, "type", -1) or -1)
    row[IDX["min_count"]] = float(sel.minCount or 0)
    row[IDX["max_count"]] = float(sel.maxCount or 0)
    row[IDX["n_options"]] = float(len(sel.option or []))
    row[IDX["remain_damage"]] = float(getattr(sel, "remainDamageCounter", 0) or 0)
    row[IDX["remain_energy"]] = float(getattr(sel, "remainEnergyCost", 0) or 0)
    row[IDX["stadium_id"]] = float(st.stadium[0].id) if st.stadium else 0.0
    cc = getattr(sel, "contextCard", None)
    row[IDX["context_card_id"]] = float(getattr(cc, "id", 0) or 0) if cc else 0.0
    row[IDX["looking_n"]] = float(len(st.looking or []))

    inplay_ids = Counter()
    for si, side in enumerate(("own", "opp")):
        ps = st.players[si ^ 0] if side == "own" else st.players[1 - yi]
        ps = st.players[yi] if side == "own" else st.players[1 - yi]
        row[IDX[f"{side}_deck"]] = float(ps.deckCount)
        row[IDX[f"{side}_hand"]] = float(ps.handCount)
        row[IDX[f"{side}_discard"]] = float(len(ps.discard))
        row[IDX[f"{side}_prize"]] = float(len(ps.prize))
        row[IDX[f"{side}_bench_n"]] = float(len(ps.bench))
        for cond in ("poisoned", "burned", "asleep", "paralyzed", "confused"):
            row[IDX[f"{side}_{cond}"]] = float(getattr(ps, cond, 0) or 0)
        pokes = list(ps.active[:1]) + list(ps.bench[:BENCH_SLOTS])
        thp = tdm = ten = 0.0
        for p in pokes:
            if p is None:
                continue
            thp += float(p.hp or 0)
            tdm += float((p.maxHp or 0) - (p.hp or 0))
            ten += float(len(p.energyCards or []))
            inplay_ids[int(p.id or 0)] += 1
        row[IDX[f"{side}_total_hp"]] = thp
        row[IDX[f"{side}_total_damage"]] = tdm
        row[IDX[f"{side}_total_energy"]] = ten
        slots = ["active"] + [f"bench{i}" for i in range(BENCH_SLOTS)]
        for k, slot in enumerate(slots):
            p = pokes[k] if k < len(pokes) else None
            _poke(row, IDX[f"{side}_{slot}_id"], p)

    hand = st.players[yi].hand or []
    disc = st.players[yi].discard or []
    hc, dc = Counter(int(c.id) for c in hand), Counter(int(c.id) for c in disc)
    for cid in DECK_IDS:
        row[IDX[f"hand_c{cid}"]] = float(hc.get(cid, 0))
        row[IDX[f"discard_c{cid}"]] = float(dc.get(cid, 0))
        row[IDX[f"inplay_c{cid}"]] = float(inplay_ids.get(cid, 0))
    for i in range(HAND_SLOTS):
        row[IDX[f"hand_pos{i}_id"]] = float(hand[i].id) if i < len(hand) else 0.0

    tc = Counter(int(o.type) for o in (sel.option or []))
    for i in range(N_OPT_TYPES):
        row[IDX[f"opt_type_count_{i}"]] = float(tc.get(i, 0))

    # what is on offer this decision, in game terms rather than option codes
    opp = st.players[1 - yi]
    own = st.players[yi]
    # `active` can be a non-empty list holding None (between a KO and the
    # replacement being chosen). 83 of 2341 teacher decisions hit exactly that,
    # and option_rows() raising there would make the shipped agent fall back to an
    # arbitrary legal move -- the same silent-degradation shape as the load_ref bug.
    opp_active = opp.active[0] if opp.active else None
    own_active = own.active[0] if own.active else None
    opp_hp = float(opp_active.hp or 0) if opp_active is not None else 0.0
    atk = _atk_table()
    best = 0.0
    for o in (sel.option or []):
        if o.attackId:
            best = max(best, float(atk.get(int(o.attackId), (0, 0))[0]))
    row[IDX["best_attack_damage"]] = best
    row[IDX["lethal_available"]] = float(opp_hp > 0 and best >= opp_hp)
    row[IDX["prize_diff"]] = float(len(own.prize) - len(opp.prize))
    row[IDX["n_attack_opts"]] = float(tc.get(int(OptionType.ATTACK), 0))
    row[IDX["n_ability_opts"]] = float(tc.get(int(OptionType.ABILITY), 0))
    row[IDX["n_evolve_opts"]] = float(tc.get(int(OptionType.EVOLVE), 0))
    row[IDX["n_play_opts"]] = float(tc.get(int(OptionType.PLAY), 0))
    row[IDX["n_end_opts"]] = float(tc.get(int(OptionType.END), 0))
    row[IDX["n_retreat_opts"]] = float(tc.get(int(OptionType.RETREAT), 0))
    if own_active is not None:
        rc = card_meta(own_active.id)[2]
        row[IDX["own_active_retreat_cost"]] = float(rc)
        row[IDX["own_active_retreat_payable"]] = float(
            len(own_active.energyCards or []) >= rc)
        mh = float(own_active.maxHp or 0)
        row[IDX["own_active_hp_ratio"]] = float(own_active.hp or 0) / mh if mh else 0.0
    if opp_active is not None:
        mh = float(opp_active.maxHp or 0)
        row[IDX["opp_active_hp_ratio"]] = opp_hp / mh if mh else 0.0
    for k in (1, 2, 3):
        h = history[-k] if len(history) >= k else None
        if h:
            row[IDX[f"prev{k}_type"]] = float(h[0])
            row[IDX[f"prev{k}_source_id"]] = float(h[1])
            row[IDX[f"prev{k}_target_id"]] = float(h[2])
            row[IDX[f"prev{k}_attack_id"]] = float(h[3])
            row[IDX[f"prev{k}_area"]] = float(h[4])
    return row


def _card_at(obs, area, index, pi):
    """Resolve an option's (area, index) to the card it refers to.

    Inlined rather than imported from train_mcts. That import only resolves in the
    dev tree: inside the submission tar it raises, the except swallowed it, and
    every option's src/tgt card id silently became 0 -- the model scored options it
    could not identify. The built artifact went 0.150/0.000/0.100 against opponents
    the dev module beat at 0.480/0.630, with zero errors reported. Ship-path and
    dev-path must run the same code.
    """
    if area is None or index is None:
        return None
    try:
        ps = obs.current.players[pi]
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
    except Exception:
        return None
    return None


def semantic(obs, o):
    """Copy-independent identity of an option: what it DOES, not which index."""
    yi = obs.current.yourIndex
    pi = o.playerIndex if o.playerIndex is not None else yi
    src = _card_at(obs, o.area, o.index, yi) if o.area is not None else None
    tgt = _card_at(obs, o.inPlayArea, o.inPlayIndex, pi) \
        if o.inPlayArea is not None else None
    if tgt is None and o.area is not None and o.playerIndex is not None:
        tgt = _card_at(obs, o.area, o.index, pi)
    return (int(o.type), int(getattr(src, "id", 0) or 0),
            int(getattr(tgt, "id", 0) or 0), int(o.attackId or 0),
            int(o.area if o.area is not None else -1),
            int(o.inPlayArea if o.inPlayArea is not None else -1))


def option_rows(obs, history=()):
    """One feature row per legal option, plus the semantic keys (for history)."""
    sel = obs.select
    opts = list(sel.option or [])
    base = base_state(obs, list(history))
    sems = [semantic(obs, o) for o in opts]
    counts = Counter(sems)
    seen = Counter()
    yi = obs.current.yourIndex
    _opp = obs.current.players[1 - yi]
    _oa = _opp.active[0] if _opp.active else None
    opp_hp = float(_oa.hp or 0) if _oa is not None else 0.0
    rows = []
    n = max(1, len(opts))
    for pos, (o, s) in enumerate(zip(opts, sems)):
        r = list(base)
        rank = seen[s]
        seen[s] += 1
        r[IDX["opt_pos"]] = float(pos)
        r[IDX["opt_pos_norm"]] = float(pos) / n
        r[IDX["opt_type"]] = float(o.type)
        r[IDX["opt_area"]] = float(o.area if o.area is not None else -1)
        r[IDX["opt_index"]] = float(o.index or 0)
        r[IDX["opt_player_rel"]] = float(
            0 if o.playerIndex is None else (0 if o.playerIndex == yi else 1))
        r[IDX["opt_inplay_area"]] = float(
            o.inPlayArea if o.inPlayArea is not None else -1)
        r[IDX["opt_inplay_index"]] = float(o.inPlayIndex or 0)
        r[IDX["opt_attack_id"]] = float(o.attackId or 0)
        r[IDX["opt_number"]] = float(o.number or 0)
        r[IDX["opt_count"]] = float(o.count or 0)
        r[IDX["opt_card_id"]] = float(o.cardId or 0)
        _, srcid, tgtid, _, _, _ = s
        for pre, cid in (("src", srcid), ("tgt", tgtid)):
            st, ct, rc, hp, ex = card_meta(cid)
            r[IDX[f"{pre}_id"]] = float(cid)
            r[IDX[f"{pre}_stage"]] = float(st)
            r[IDX[f"{pre}_type"]] = float(ct)
            r[IDX[f"{pre}_retreat"]] = float(rc)
            r[IDX[f"{pre}_meta_hp"]] = float(hp)
            r[IDX[f"{pre}_ex"]] = float(ex)
        pi = o.playerIndex if o.playerIndex is not None else yi
        tp = _card_at(obs, o.inPlayArea, o.inPlayIndex, pi) \
            if o.inPlayArea is not None else None
        if tp is not None and hasattr(tp, "hp"):
            r[IDX["tgt_cur_hp"]] = float(tp.hp or 0)
            r[IDX["tgt_maxhp"]] = float(tp.maxHp or 0)
            r[IDX["tgt_damage"]] = float((tp.maxHp or 0) - (tp.hp or 0))
            r[IDX["tgt_energy_n"]] = float(len(getattr(tp, "energyCards", []) or []))
            r[IDX["tgt_appear"]] = float(getattr(tp, "appearThisTurn", 0) or 0)
        r[IDX["tgt_is_active"]] = float(o.inPlayArea == AreaType.ACTIVE) \
            if o.inPlayArea is not None else 0.0
        r[IDX["tgt_is_own"]] = float(pi == yi)
        # An attack option is the only place the row can say "this ends the
        # opponent's Pokemon". Without it the tree has to memorise attackId ->
        # damage, which is why ATTACK was the most-dropped option type.
        if o.attackId:
            dmg, ecost = _atk_table().get(int(o.attackId), (0, 0))
            r[IDX["opt_attack_damage"]] = float(dmg)
            r[IDX["opt_attack_energy"]] = float(ecost)
            r[IDX["opt_attack_lethal"]] = float(opp_hp > 0 and dmg >= opp_hp)
            r[IDX["opt_attack_margin"]] = float(dmg - opp_hp)
        r[IDX["dup_count"]] = float(counts[s])
        r[IDX["dup_rank"]] = float(rank)
        rows.append(r)
    return rows, sems
