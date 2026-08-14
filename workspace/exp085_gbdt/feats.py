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

# The 60-card list is fixed for a given submission, so per-card counters are a
# fixed width -- but WHICH 60 is now a parameter. The default is the Grimmsnarl
# (オーロンゲ) list every model up to v055 was trained on; set_deck() swaps it,
# and PTCG_DECK_JSON lets the corpus builder and the trainers agree on a deck
# without editing this file. The shipped main.py calls set_deck() with the
# deck.csv it carries, so the feature width can never drift from the model.
DEFAULT_DECK = [7] * 10 + [104] * 2 + [112] * 4 + [646] * 4 + [647] * 3 + \
    [648] * 3 + [860] * 2 + [1079] * 3 + [1080] + [1086] * 4 + [1097] * 3 + \
    [1122] + [1137] + [1152] * 4 + [1182] * 2 + [1219] * 4 + [1227] * 4 + \
    [1231] + [1259] * 4
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


_CHEAP = {}


def _cheapest_attack(cid):
    """Energy count of the cheapest attack a card has, 0 if it has none.

    Used to turn "attach an energy here" into "how many more does this Pokemon
    need before it can swing", which is the question the teacher is answering.
    """
    cid = int(cid or 0)
    if cid not in _CHEAP:
        global _CD
        if _CD is None:
            _CD = {int(c.cardId): c for c in all_card_data()}
        c = _CD.get(cid)
        atk = _atk_table()
        costs = [atk[int(a)][1] for a in (getattr(c, "attacks", None) or [])
                 if int(a) in atk]
        _CHEAP[cid] = min(costs) if costs else 0
    return _CHEAP[cid]


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


# The opponent cards worth naming.
#
# Everything the row said about the other side was an AGGREGATE -- bench count,
# total energy, best attack damage. That is enough to pilot our own deck but it
# throws away the thing a human actually reads: which cards are on the table.
# Mist Energy on their active changes whether Munkidori's damage-move plan works;
# Air Balloon changes whether a gust actually traps anything; Jamming Tower turns
# our Tools off. None of that is expressible as a count of energies.
#
# The list is the union of the current archetypes' most common lists, weighted by
# their 08-12 share, PLUS our own 19. Excluding ours was the first attempt's
# mistake: they are covered on our side of the board, not on theirs, so in the
# mirror every added column was zero and the heaviest cell fell 0.593 -> 0.541.
# Two columns each: how many are on their board (including attached energy and
# tools) and how many are in their discard.
# Written out literally, not read from opp_cards.json: the built agent inlines
# this module into a single main.py and ships no data files beside it, so a file
# read here would return [] inside the sandbox, silently drop 80 columns, and
# leave the model reading a row that does not match what it was trained on.
# regen: uv run python opp_cards_gen.py
OPP_CARDS = \
    [1121, 5, 1225, 19, 2, 119, 120, 1120, 305, 6, 11, 162, 163, 1188, 1248,
    756, 121, 1198, 1229, 66, 1146, 1087, 1264, 140, 1213, 235, 1246, 1197,
    3, 1174, 1071, 741, 742, 743, 1081, 144, 183, 184, 1123, 848, 7, 104,
    112, 646, 647, 648, 860, 1079, 1080, 1086, 1097, 1122, 1137, 1152, 1182,
    1219, 1227, 1231, 1259]


# How strong was the player who produced this row, as a rank within their OWN day?
#
# The absolute-score filter we shipped as v055 (>= 1075) turned out to be a date
# filter in disguise: the ladder's score level fell through August, so 1075 kept
# 77% of 07-26 teachers but only 29% of 08-08 teachers. It therefore threw away
# exactly the recent games we most wanted, and measured as worth nothing
# (0.545 vs 0.541 head-to-head, n=1600).
#
# Conditioning replaces filtering. Every decision is kept, and the row simply says
# where its author stood that day (0 = bottom, 1 = top). At inference we ask for
# 1.0 -- "play like the best player of the day". Reported externally by Amedeo
# Biolatti (disc732905): conditioning on rating gave +2% accuracy and ~+2% winrate
# over conditioning on a mid rating, and extrapolated above the training range.
TEACHER_PCT = 1.0


def _names():
    f = ["turn", "turn_action_count", "first_player", "energy_attached",
         "supporter_played", "stadium_played", "retreated", "context",
         "select_type", "min_count", "max_count", "n_options",
         "remain_damage", "remain_energy", "stadium_id", "context_card_id",
         "looking_n", "teacher_pct"]
    for cid in OPP_CARDS:
        f += [f"oc_play_{cid}", f"oc_disc_{cid}"]
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
    # --- what has already happened THIS TURN ---
    # diag_errors on v3: ABILITY is promoted 1.46x more often than the teacher
    # takes it and Munkidori (the damage-transfer ability) is the single most
    # over-promoted card (1720 + 1168 wrong promotions). prev1..3 only reaches
    # three decisions back, so a model deciding the eighth action of a turn cannot
    # tell "I already moved damage twice" from "I have not started". These are
    # scoped to the current turn and reset when it changes.
    f += ["turn_actions_so_far", "turn_abilities_used", "turn_plays_used",
          "turn_attaches_used", "turn_evolves_used"]
    # --- state-level answers to "is stopping / swinging / retreating right?" ---
    # --- ability / attachment preconditions ---
    # diag_errors on v4 still shows ABILITY promoted 1.43x more often than the
    # teacher takes it, and the single most over-promoted option is Munkidori
    # (3,137 wrong promotions across two forms). Its ability, Adrena-Brain, is
    # "once per turn, IF this Pokemon has {D} Energy attached, move up to 3 damage
    # counters from one of your Pokemon to one of your opponent's". None of those
    # preconditions were visible: not the energy, not whether we have counters to
    # move, not whether moving them finishes anything. Same shape as the missing
    # attack damage in v3 and the missing turn history in v4.
    f += ["own_movable_counters", "opp_active_counters_to_ko",
          "move3_would_ko", "own_dark_energy_total"]
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
          # per-option: has THIS action already been taken this turn, and does a
          # damage-counter placement here actually finish the target?
          "opt_src_acted_this_turn", "opt_same_action_this_turn",
          "opt_counters_to_ko", "opt_tgt_hp_ratio",
          # per-option preconditions: can this ability source actually fire, and
          # does this attachment bring its target closer to attacking?
          "opt_src_dark_energy", "opt_src_energy_n",
          "opt_tgt_energy_need", "opt_tgt_need_after",
          "dup_count", "dup_rank"]
    # --- v6: what a SEARCH is actually for (c7 / TO_HAND) ---
    # diag_errors on v4b: TO_HAND is 3,741 of 17,320 errors (21.6%) at top-k
    # 0.6437, and unlike every other family it did NOT improve when the trees went
    # from 63 to 511 leaves. That is the signature of a missing feature, not of
    # missing capacity.
    #
    # Deciding what to fetch is a question about the DECK and the EVOLUTION CHAIN,
    # and the row could not express either. hand_c{cid}/discard_c{cid} exist, but
    # only as 19 separate columns: to use them a tree would have to first split on
    # opt_card_id and then on the matching counter, relearning the join 19 times.
    # These project the counters onto the option being scored, so "I already hold
    # two of these" is one split instead of two.
    #
    # The chain features answer the other half. Fetching Marnie's Grimmsnarl ex is
    # right when Morgrem is on the board or Rare Candy is in hand over a
    # Impidimp, and wrong otherwise -- a distinction nothing in v4b could draw.
    f += ["opt_hand_count", "opt_discard_count", "opt_inplay_count",
          "opt_copies_unseen", "opt_evo_base_in_play", "opt_evo_base_in_hand",
          "opt_evo_next_in_hand", "opt_evo_candy_ready", "opt_playable_now",
          "own_bench_free"]
    # --- v8: what the OPPONENT can do to us ---
    # /meta-watch on v054: 42% of our ladder games are the Grimmsnarl (オーロンゲ)
    # mirror, and until now the row said almost nothing about the other side
    # beyond raw HP and energy counts. Two separate gaps, grounded in how the deck
    # actually plays:
    #
    # 1. THREAT. own_movable_counters told the model how much Adrena-Brain fuel WE
    #    had; there was no opposite number. A Munkidori (マシマシラ) with a {D}
    #    Energy attached moves up to 3 damage counters, so "their best attack" is
    #    not their attack damage -- it is attack damage plus 30 they can shuffle
    #    across the board. Without it the model cannot tell a safe Active from one
    #    that dies next turn.
    #
    # 2. DECK TRACKING, valid only in the mirror. Their 60 cards are ours, their
    #    discard and board are fully visible, so unseen = our count minus what we
    #    can see, and that unseen pile is split between hand, deck and prizes.
    #    The card this matters most for is Boss's Orders (ボスの指令), 2 copies:
    #    it drags a benched Pokemon into the Active spot. Whether they plausibly
    #    hold one decides if it is safe to bench a damaged Munkidori or a second
    #    Grimmsnarl ex -- and an ex on the bench is 2 prizes handed over.
    #    opp_is_mirror / opp_seen_offdeck let the trees switch these off when the
    #    opponent turns out to be running something else.
    #
    # Prize math is the third piece. An ex KO gives 2 prizes (Mega ex 3), so
    # "how many more KOs until each side wins" is not len(prize) alone -- it
    # depends on what is standing. That is the arithmetic a human plays by and
    # nothing in the row expressed it.
    f += ["opp_is_mirror", "opp_seen_offdeck", "opp_hand_frac",
          "opp_unseen_boss", "opp_exp_boss_in_hand", "opp_unseen_candy",
          "opp_unseen_acespec", "opp_unseen_primary_ex", "opp_unseen_munkidori",
          "opp_unseen_energy", "opp_unseen_poffin", "opp_unseen_stretcher",
          "opp_movable_counters", "opp_munkidori_ready", "opp_best_attack_damage",
          "opp_attack_ready", "opp_threat_total", "opp_can_ko_our_active",
          "opp_dark_energy_total",
          "own_active_prize_value", "opp_active_prize_value",
          "own_bench_prize_max", "opp_bench_prize_max", "own_bench_gust_risk"]
    return f


# Cards whose remaining copies change how the mirror is played. These are ROLES,
# resolved against whatever deck is loaded, so the same feature code works for a
# different archetype: the gust card, the evolution shortcut, the ACE SPEC, the
# biggest ex, the damage-mover, the basic-Pokemon search and the recovery card.
# A role the deck does not run resolves to 0, and every lookup that uses it then
# returns 0 rather than a wrong count.
ROLE_NAMES = {
    "BOSS": ("Boss's Orders", "Boss’s Orders"),   # two apostrophe encodings exist
    "RARE_CANDY_ID": ("Rare Candy",),
    "MUNKIDORI": ("Munkidori",),                  # Adrena-Brain moves 3 counters
    "POFFIN": ("Buddy-Buddy Poffin",),
    "STRETCHER": ("Night Stretcher",),
}
BOSS = RARE_CANDY_ID = ACE_SPEC = PRIMARY_EX = 0
MUNKIDORI = POFFIN = STRETCHER = 0
DARK_ENERGY = 7      # rebound by set_deck to the deck's main basic Energy


def prize_value(cid):
    """Prizes the opponent takes for knocking this Pokemon out.

    Mega ex are worth 3, ex 2, everything else 1. card_meta's ex_rank already
    separates megaEx / ex / tera, so this is a relabelling rather than new
    lookups. Our line hands over 2 for every Grimmsnarl ex, which is why benching
    a second one while they may hold Boss's Orders is a real cost.
    """
    ex = card_meta(cid)[4]
    return 3.0 if ex == 3 else (2.0 if ex == 2 else 1.0)


# Copies of each card in OUR 60. Inlined rather than read from
# exp080_bc/grimmsnarl_deck.json because feats.py is concatenated into the
# shipped main.py, where that file does not exist.
DECK_COUNT = {7: 10, 104: 2, 112: 4, 646: 4, 647: 3, 648: 3, 860: 2, 1079: 3,
              1080: 1, 1086: 4, 1097: 3, 1122: 1, 1137: 1, 1152: 4, 1182: 2,
              1219: 4, 1227: 4, 1231: 1, 1259: 4}
RARE_CANDY = 1079
_EVO = None


def _evo_tables():
    """(evolves_from[cid] -> (pre-evolution ids,), evolves_to[cid] -> [successor ids]).

    CardData.evolvesFrom is the pre-evolution's NAME, so this resolves names back
    to ids once at import. A name maps to SEVERAL ids -- Snorunt is 103 and 860,
    and our deck runs 860 -- so the pre-evolution is kept as the full id tuple and
    counted across all of them. Taking the first id instead made Froslass look for
    a Snorunt we never play, and the feature would have been silently zero.
    """
    global _EVO, _CD
    if _EVO is None:
        if _CD is None:
            _CD = {int(c.cardId): c for c in all_card_data()}
        by_name = {}
        for cid, c in _CD.items():
            by_name.setdefault(str(getattr(c, "name", "") or ""), []).append(cid)
        frm, to = {}, {}
        for cid, c in _CD.items():
            nm = getattr(c, "evolvesFrom", None)
            if not nm:
                continue
            pres = by_name.get(str(nm), [])
            if pres:
                frm[cid] = tuple(pres)
            for p in pres:
                to.setdefault(p, []).append(cid)
        _EVO = (frm, to)
    return _EVO


def set_deck(cards):
    """Point every deck-dependent global at a new 60-card list.

    Per-card counters are one column per distinct card, so the ROW WIDTH depends
    on the deck (19 distinct cards for Grimmsnarl / オーロンゲ, 21 for the
    Mega Lopunny ex / メガミミロップex list). Training and inference must agree,
    which is why build_submission bakes a set_deck() call into main.py from the
    deck.csv it ships rather than leaving the default in place.

    Card ROLES are resolved here instead of hardcoded: the gust card, the
    evolution shortcut, the ACE SPEC, the biggest ex, the damage-mover, the basic
    search and the recovery card. A role the deck does not run stays 0, and the
    features that use it then read 0 rather than someone else's count.
    """
    global DECK, DECK_IDS, DECK_COUNT, FEATURES, IDX, N_FEATURES, CATEGORICAL
    global BOSS, RARE_CANDY_ID, ACE_SPEC, PRIMARY_EX, MUNKIDORI, POFFIN
    global STRETCHER, DARK_ENERGY, RARE_CANDY, _CD
    cards = [int(x) for x in cards]
    DECK = cards
    DECK_COUNT = dict(Counter(cards))
    DECK_IDS = sorted(DECK_COUNT)
    if _CD is None:
        _CD = {int(c.cardId): c for c in all_card_data()}

    def by_name(names):
        for cid in DECK_IDS:
            c = _CD.get(cid)
            if c is not None and str(getattr(c, "name", "")) in names:
                return cid
        return 0

    BOSS = by_name(ROLE_NAMES["BOSS"])
    RARE_CANDY_ID = RARE_CANDY = by_name(ROLE_NAMES["RARE_CANDY_ID"])
    MUNKIDORI = by_name(ROLE_NAMES["MUNKIDORI"])
    POFFIN = by_name(ROLE_NAMES["POFFIN"])
    STRETCHER = by_name(ROLE_NAMES["STRETCHER"])
    # the ACE SPEC is one per deck by rule, so "the ace spec card" is unambiguous
    ACE_SPEC = next((cid for cid in DECK_IDS
                         if getattr(_CD.get(cid), "aceSpec", False)), 0)
    # the main attacker: highest-HP ex / Mega ex, i.e. the 2-or-3-prize liability
    exs = [(card_meta(cid)[3], cid) for cid in DECK_IDS if card_meta(cid)[4] >= 2]
    PRIMARY_EX = max(exs)[1] if exs else 0
    # the basic Energy the deck runs most of -- attack costs are paid in it
    ens = [(DECK_COUNT[cid], cid) for cid in DECK_IDS
           if card_meta(cid)[1] == 5 and _CD.get(cid) is not None
           and getattr(_CD[cid], "basic", False)]
    if not ens:      # cardType 5 = Energy; fall back to any Energy in the list
        ens = [(DECK_COUNT[cid], cid) for cid in DECK_IDS if card_meta(cid)[1] == 5]
    DARK_ENERGY = max(ens)[1] if ens else 0

    FEATURES = _names()
    IDX = {n: i for i, n in enumerate(FEATURES)}
    N_FEATURES = len(FEATURES)
    # Trees split on ordered values; ids and enum codes are categorical. LightGBM
    # is told which is which so it does not read "card 1259 > card 7" as a size.
    CATEGORICAL = [n for n in FEATURES if n.endswith("_id") or n in (
        "context", "select_type", "opt_type", "opt_area", "opt_inplay_area",
        "src_type", "tgt_type", "prev1_area", "prev2_area", "prev3_area",
        "prev1_type", "prev2_type", "prev3_type")]


set_deck(DEFAULT_DECK)
# One env var keeps the corpus builder, the trainers and the exporter on the same
# deck without editing this file or passing a flag through five scripts.
if os.environ.get("PTCG_DECK_JSON"):
    import json as _json
    set_deck(_json.load(open(os.environ["PTCG_DECK_JSON"])))


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
    row[IDX["teacher_pct"]] = float(TEACHER_PCT)

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
    # counters we could move (Adrena-Brain's raw material) and what it takes to
    # finish the opponent's Active
    movable = 0.0
    for p in (list(own.active[:1]) + list(own.bench[:BENCH_SLOTS])):
        if p is not None:
            movable += ((p.maxHp or 0) - (p.hp or 0)) / 10.0
    row[IDX["own_movable_counters"]] = movable
    need = -(-opp_hp // 10.0) if opp_hp > 0 else 0.0
    row[IDX["opp_active_counters_to_ko"]] = need
    row[IDX["move3_would_ko"]] = float(need > 0 and min(3.0, movable) >= need)
    dark = 0.0
    for p in (list(own.active[:1]) + list(own.bench[:BENCH_SLOTS])):
        if p is not None:
            dark += sum(1 for e in (p.energies or []) if int(e) == DARK_ENERGY)
    row[IDX["own_dark_energy_total"]] = dark
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
    # history entries are (turn, semantic). Older callers passed bare semantics;
    # accept both so a stale corpus does not silently shift every prev* field.
    hist = [(h[0], h[1]) if isinstance(h, tuple) and len(h) == 2 and isinstance(h[1], tuple)
            else (None, h) for h in history]
    for k in (1, 2, 3):
        h = hist[-k][1] if len(hist) >= k else None
        if h:
            row[IDX[f"prev{k}_type"]] = float(h[0])
            row[IDX[f"prev{k}_source_id"]] = float(h[1])
            row[IDX[f"prev{k}_target_id"]] = float(h[2])
            row[IDX[f"prev{k}_attack_id"]] = float(h[3])
            row[IDX[f"prev{k}_area"]] = float(h[4])
    this_turn = [h for (t, h) in hist if t is None or t == st.turn]
    row[IDX["turn_actions_so_far"]] = float(len(this_turn))
    row[IDX["turn_abilities_used"]] = float(
        sum(1 for h in this_turn if h[0] == int(OptionType.ABILITY)))
    row[IDX["turn_plays_used"]] = float(
        sum(1 for h in this_turn if h[0] == int(OptionType.PLAY)))
    row[IDX["turn_attaches_used"]] = float(
        sum(1 for h in this_turn if h[0] == int(OptionType.ATTACH)))
    row[IDX["turn_evolves_used"]] = float(
        sum(1 for h in this_turn if h[0] == int(OptionType.EVOLVE)))
    row[IDX["own_bench_free"]] = float(BENCH_SLOTS - len(own.bench or []))
    _opp_view(row, st, yi)
    return row


def _opp_view(row, st, yi):
    """Everything the rules let us know about the other side.

    Split out of base_state only for length; it runs on every decision.
    """
    opp = st.players[1 - yi]
    own = st.players[yi]
    opp_pokes = [p for p in (list(opp.active[:1]) + list(opp.bench[:BENCH_SLOTS]))
                 if p is not None]
    own_pokes = [p for p in (list(own.active[:1]) + list(own.bench[:BENCH_SLOTS]))
                 if p is not None]
    opp_active = opp.active[0] if opp.active else None
    own_active = own.active[0] if own.active else None

    # --- what we have SEEN of their 60 --------------------------------------
    seen = Counter()
    disc = Counter()
    play = Counter()
    off = 0
    for c in (opp.discard or []):
        cid = int(getattr(c, "id", 0) or 0)
        seen[cid] += 1
        disc[cid] += 1
    for p in opp_pokes:
        seen[int(p.id or 0)] += 1
        play[int(p.id or 0)] += 1
        for e in (p.energyCards or []):
            cid = int(getattr(e, "id", 0) or 0)
            seen[cid] += 1
            play[cid] += 1
        for t in (p.tools or []):
            cid = int(getattr(t, "id", 0) or 0)
            seen[cid] += 1
            play[cid] += 1
    for cid in OPP_CARDS:
        if play.get(cid):
            row[IDX[f"oc_play_{cid}"]] = float(play[cid])
        if disc.get(cid):
            row[IDX[f"oc_disc_{cid}"]] = float(disc[cid])
    for cid, n in seen.items():
        over = n - DECK_COUNT.get(cid, 0)
        if over > 0:
            off += over          # a card they cannot be running, or too many of it
    row[IDX["opp_seen_offdeck"]] = float(off)
    row[IDX["opp_is_mirror"]] = float(off == 0)

    # unseen copies are somewhere in hand + deck + prizes; the hand share is the
    # part that can be used against us THIS turn
    hand_n = float(opp.handCount or 0)
    hidden = hand_n + float(opp.deckCount or 0) + float(len(opp.prize or []))
    frac = hand_n / hidden if hidden > 0 else 0.0
    row[IDX["opp_hand_frac"]] = frac

    def unseen(cid):
        return float(max(0, DECK_COUNT.get(cid, 0) - seen.get(cid, 0)))

    ub = unseen(BOSS)
    row[IDX["opp_unseen_boss"]] = ub
    row[IDX["opp_exp_boss_in_hand"]] = ub * frac
    row[IDX["opp_unseen_candy"]] = unseen(RARE_CANDY_ID)
    row[IDX["opp_unseen_acespec"]] = unseen(ACE_SPEC)
    row[IDX["opp_unseen_primary_ex"]] = unseen(PRIMARY_EX)
    row[IDX["opp_unseen_munkidori"]] = unseen(MUNKIDORI)
    row[IDX["opp_unseen_energy"]] = unseen(DARK_ENERGY)
    row[IDX["opp_unseen_poffin"]] = unseen(POFFIN)
    row[IDX["opp_unseen_stretcher"]] = unseen(STRETCHER)

    # --- what they can do to us NEXT turn -----------------------------------
    # Adrena-Brain fuel: damage already sitting on THEIR Pokemon is ammunition,
    # not just a weakness, because Munkidori moves it onto ours.
    movable = 0.0
    dark = 0.0
    munki_ready = 0.0
    for p in opp_pokes:
        movable += ((p.maxHp or 0) - (p.hp or 0)) / 10.0
        d = sum(1 for e in (p.energies or []) if int(e) == DARK_ENERGY)
        dark += d
        if int(p.id or 0) == MUNKIDORI and d > 0:
            munki_ready = 1.0
    row[IDX["opp_movable_counters"]] = movable
    row[IDX["opp_dark_energy_total"]] = dark
    row[IDX["opp_munkidori_ready"]] = munki_ready

    atk = _atk_table()
    best = 0.0
    ready = 0.0
    if opp_active is not None:
        have = len(opp_active.energyCards or [])
        _CDl = _CD if _CD is not None else None
        if _CDl is None:
            card_meta(opp_active.id)          # forces _CD to load
            _CDl = _CD
        c = _CDl.get(int(opp_active.id or 0))
        for aid in (getattr(c, "attacks", None) or []):
            dmg, ecost = atk.get(int(aid), (0, 0))
            if ecost <= have:
                ready = 1.0
                best = max(best, float(dmg))
    row[IDX["opp_best_attack_damage"]] = best
    row[IDX["opp_attack_ready"]] = ready
    # a damage counter is 10 HP and Adrena-Brain moves at most 3
    threat = best + 10.0 * min(3.0, movable) * munki_ready
    row[IDX["opp_threat_total"]] = threat
    own_hp = float(own_active.hp or 0) if own_active is not None else 0.0
    row[IDX["opp_can_ko_our_active"]] = float(own_hp > 0 and threat >= own_hp)

    # --- prize arithmetic ----------------------------------------------------
    row[IDX["own_active_prize_value"]] = (
        prize_value(own_active.id) if own_active is not None else 0.0)
    row[IDX["opp_active_prize_value"]] = (
        prize_value(opp_active.id) if opp_active is not None else 0.0)
    own_bench_max = max([prize_value(p.id) for p in own_pokes[1:]] or [0.0])
    row[IDX["own_bench_prize_max"]] = own_bench_max
    row[IDX["opp_bench_prize_max"]] = max(
        [prize_value(p.id) for p in opp_pokes[1:]] or [0.0])
    # the cost of leaving a 2-prize Pokemon on the bench, scaled by how likely
    # they are holding the card that drags it out
    row[IDX["own_bench_gust_risk"]] = own_bench_max * ub * frac


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
    _turn = obs.current.turn
    _hist = [(h[0], h[1]) if isinstance(h, tuple) and len(h) == 2
             and isinstance(h[1], tuple) else (None, h) for h in history]
    _this_turn = [h for (t, h) in _hist if t is None or t == _turn]
    _src_acted = Counter(h[1] for h in _this_turn)
    _same_acted = Counter(_this_turn)
    # per-option projections of the deck / evolution state (see _names v6 note)
    _own = obs.current.players[yi]
    _hand_c = Counter(int(c.id or 0) for c in (_own.hand or []))
    _disc_c = Counter(int(c.id or 0) for c in (_own.discard or []))
    _inplay_c = Counter()
    for _p in (list(_own.active[:1]) + list(_own.bench[:BENCH_SLOTS])):
        if _p is not None:
            _inplay_c[int(_p.id or 0)] += 1
    _evo_from, _evo_to = _evo_tables()
    _bench_free = BENCH_SLOTS - len(_own.bench or [])
    _sup_played = bool(obs.current.supporterPlayed)
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
        # Resolve the targeted Pokemon the same way semantic() does. A
        # DAMAGE_COUNTER option names its target through area/index with an
        # explicit playerIndex, NOT through inPlayArea, so the inPlayArea-only
        # lookup left every counter feature at zero on exactly the contexts they
        # were added for.
        tp = _card_at(obs, o.inPlayArea, o.inPlayIndex, pi) \
            if o.inPlayArea is not None else None
        if tp is None and o.area is not None and o.playerIndex is not None:
            tp = _card_at(obs, o.area, o.index, pi)
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
        sp = _card_at(obs, o.area, o.index, yi) if o.area is not None else None
        if sp is not None and getattr(sp, "energies", None) is not None:
            r[IDX["opt_src_dark_energy"]] = float(
                sum(1 for e in (sp.energies or []) if int(e) == DARK_ENERGY))
            r[IDX["opt_src_energy_n"]] = float(len(sp.energyCards or []))
        if tp is not None and getattr(tp, "id", None):
            cheapest = _cheapest_attack(tp.id)
            if cheapest:
                have = len(getattr(tp, "energyCards", []) or [])
                r[IDX["opt_tgt_energy_need"]] = float(max(0, cheapest - have))
                r[IDX["opt_tgt_need_after"]] = float(max(0, cheapest - have - 1))
        r[IDX["opt_src_acted_this_turn"]] = float(_src_acted.get(s[1], 0))
        r[IDX["opt_same_action_this_turn"]] = float(_same_acted.get(s, 0))
        # A damage counter is 10 HP. Placing/removing them is the deck's main
        # mechanic, and the model had no way to see whether a placement finishes
        # the target -- the same blind spot attack damage had before v3.
        if tp is not None and getattr(tp, "hp", None):
            # counters_to_ko: a damage counter is 10 HP, so this is how many more
            # it takes to finish the target -- the deck's main mechanic, and
            # invisible to the model before now.
            # hp_ratio: trees split on thresholds, they cannot form hp/maxHp
            # themselves, and "nearly dead" is what matters, not absolute HP.
            # (remainDamageCounter is always 0 in replay observations, so a
            # "counters are sufficient" flag would never fire -- checked, dropped.)
            r[IDX["opt_counters_to_ko"]] = -(-float(tp.hp) // 10.0)
            mh = float(getattr(tp, "maxHp", 0) or 0)
            r[IDX["opt_tgt_hp_ratio"]] = float(tp.hp) / mh if mh else 0.0
        r[IDX["dup_count"]] = float(counts[s])
        r[IDX["dup_rank"]] = float(rank)
        # --- v6: the option as a CARD, joined to deck / chain state ---
        ocid = int(o.cardId or 0) or int(srcid or 0)
        if ocid:
            hcn = _hand_c.get(ocid, 0)
            dcn = _disc_c.get(ocid, 0)
            icn = _inplay_c.get(ocid, 0)
            r[IDX["opt_hand_count"]] = float(hcn)
            r[IDX["opt_discard_count"]] = float(dcn)
            r[IDX["opt_inplay_count"]] = float(icn)
            r[IDX["opt_copies_unseen"]] = float(
                max(0, DECK_COUNT.get(ocid, 0) - hcn - dcn - icn))
            pres = _evo_from.get(ocid) or ()
            if pres:
                r[IDX["opt_evo_base_in_play"]] = float(
                    sum(_inplay_c.get(p, 0) for p in pres))
                r[IDX["opt_evo_base_in_hand"]] = float(
                    sum(_hand_c.get(p, 0) for p in pres))
                # Rare Candy skips the middle stage, so a Stage 2/3 is live when
                # the BASIC of its line is down and a Candy is in hand.
                roots = pres
                for _ in range(3):
                    nxt = tuple(q for p in roots for q in (_evo_from.get(p) or ()))
                    if not nxt:
                        break
                    roots = nxt
                r[IDX["opt_evo_candy_ready"]] = float(
                    _hand_c.get(RARE_CANDY, 0) > 0
                    and any(_inplay_c.get(p, 0) for p in roots))
            r[IDX["opt_evo_next_in_hand"]] = float(
                sum(_hand_c.get(nc, 0) for nc in _evo_to.get(ocid, ())))
            st_, ct_, _, _, _ = card_meta(ocid)
            if ct_ == 3:                       # Supporter: one per turn
                playable = not _sup_played
            elif st_ == 1 and ct_ == 0:        # Basic Pokemon: needs a bench slot
                playable = _bench_free > 0
            else:
                playable = True
            r[IDX["opt_playable_now"]] = float(playable)
        rows.append(r)
    return rows, sems
