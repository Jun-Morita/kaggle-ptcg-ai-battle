"""exp038 — depth-2 alpha-beta search (our turn + opponent's reply) on the v012
pilot, incorporating the full design-review revision:
  1. archetype-matched opponent model (opponent_model.py) instead of our own
     deck's policy for ranking/simulating the OPPONENT's moves;
  2. a richer eval_fn adding a "threat removed" term (opponent board's total
     remaining attacking potential, prize-weighted) alongside prize/hp margins;
  3. probe-based move ordering + alpha-beta pruning (both inside search_lib.py);
  4. real multi-select handling (delegated to policies, small neighbor alts).

Qualification: fire only when, in ALL K determinizations, the search's own best
action beats the BASE policy's action under an IDENTICAL search/eval (same
determinization, forced_first comparison) — upside-only, same lineage as v013's
doom veto and exp035's turn-beam.

Env: B2_K (2), B2_BRANCH (8), B2_OPP_BRANCH (4), B2_PROBE_CAP (12),
     B2_BUDGET (600), B2_OPP_MODE (minimax), RB=50.
"""
from __future__ import annotations
import os
import random
import sys
import types
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp023_revenge"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
import revenge_policy as P  # noqa
from search_lib import SearchConfig, search_best_action, default_eval, default_snapshot, _board_hp, NEG_INF  # noqa
from opponent_model import OpponentModel  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
_all_cards = {c.cardId: c for c in api.all_card_data()}


def _prize_value(card_id):
    d = _all_cards.get(card_id)
    if d is None:
        return 1
    return 3 if getattr(d, "megaEx", False) else 2 if getattr(d, "ex", False) else 1


def _board_threat(player):
    """Sum of (prize value if KO'd) * (remaining HP fraction) over a player's
    board — a rough proxy for "how much attacking potential is still standing",
    weighted by how costly (in prizes) removing it would be. Falling HP on a
    high-prize target lowers this faster than the same HP loss on a 1-prize body."""
    tot = 0.0
    for m in list(player.active or []) + list(player.bench or []):
        if m is None:
            continue
        hp = getattr(m, "hp", 0) or 0
        max_hp = getattr(m, "maxHp", 0) or hp or 1
        tot += _prize_value(m.id) * (hp / max_hp if max_hp else 0.0)
    return tot


def rich_snapshot(cur0, my):
    d = default_snapshot(cur0, my)
    d["opp_threat"] = _board_threat(cur0.players[1 - my])
    d["my_threat"] = _board_threat(cur0.players[my])
    return d


def rich_eval(cur, my, base):
    """default_eval's (prize_margin, hp_margin) extended with a "threat removed"
    middle term: the drop in the OPPONENT's total prize-weighted board threat
    minus the drop in OURS, since the root snapshot. Ordering: prize_margin (an
    actual KO/win is worth more than any amount of threat reduction) > threat
    margin (removing/weakening a 2-prize attacker beats chipping a 1-prize body)
    > raw hp margin (fine-grained tiebreak)."""
    pm, hm = default_eval(cur, my, base)
    if cur is None or pm >= 1e5 or pm <= -1e5:      # terminal (win/loss) - keep as-is
        return (pm, 0.0, hm)
    me, opp = cur.players[my], cur.players[1 - my]
    opp_threat_drop = base["opp_threat"] - _board_threat(opp)
    my_threat_drop = base["my_threat"] - _board_threat(me)
    return (pm, opp_threat_drop - my_threat_drop, hm)


def _meaningfully_better(c, b):
    """v013/v014's verified-override philosophy required a CHUNKY margin (an
    actual extra prize, or +30 damage) to fire -- never a bare epsilon. This
    search's eval tuple is continuous (HP/threat margins) and each K-iteration
    checks only ONE random hidden-info determinization, so a bare `c > b` fires
    on pure sampling noise very often (empirically ~20-50% of decisions, vs
    v013/v014's ~1-3%) without any real, robust advantage. Require the same
    kind of margin here, component by component (prize margin first, then the
    threat term, then raw HP as a last tiebreak)."""
    if len(c) == 3:
        cpm, cth, chp = c
        bpm, bth, bhp = b
    else:
        cpm, chp = c
        bpm, bhp = b
        cth = bth = 0.0
    if cpm - bpm >= 1.0:
        return True
    if cpm - bpm <= -1.0:
        return False
    if cth - bth >= 0.5:
        return True
    if cth - bth <= -0.5:
        return False
    return (chp - bhp) >= 30


def _snap_mod(mod):
    """Generic cross-turn-state snapshot for a policy module: the SAME bug
    class as revenge_policy's `_rev` (a stateful global assumes a single
    chronological playthrough, but is called across many non-chronological
    hypothetical search branches) applies to EVERY archetype-matched opponent
    pilot that tracks its own turn history (confirmed present in the Dragapult
    3rd-party pilot: pre_turn_log/current_turn_log/plan_a/plan_b, and the
    Archaludon pilot: _opp_last_attack_id/_cur_turn_logs) -- but unlike `_rev`,
    we don't know each pilot's exact stateful variable names, so this snapshots
    every top-level list/dict/scalar module global generically (skipping
    functions/classes/modules and large read-only lookup tables, which are
    reassigned wholesale rather than mutated, so staleness there is harmless)."""
    if mod is None:
        return None
    snap = {}
    for k, v in vars(mod).items():
        if k.startswith("__") or callable(v) or isinstance(v, (type, types.ModuleType)):
            continue
        if isinstance(v, list):
            snap[k] = list(v)
        elif isinstance(v, dict):
            snap[k] = dict(v)
        elif isinstance(v, (int, float, str, bool)) or v is None:
            snap[k] = v
    return snap


def _restore_mod(mod, snap):
    if mod is None or snap is None:
        return
    for k, v in snap.items():
        cur = getattr(mod, k, None)
        if isinstance(v, list) and isinstance(cur, list):
            cur[:] = v
        elif isinstance(v, dict) and isinstance(cur, dict):
            cur.clear()
            cur.update(v)
        else:
            setattr(mod, k, v)


def _is_horizon_dodge(select, base_idx, cand_idx):
    """Classic minimax HORIZON EFFECT: a shallow (depth=2) search sees the
    opponent's counter-KO after we act, but not that DECLINING to act (END
    instead) only DELAYS that same loss past its lookahead -- it looks like
    "avoided the loss" when it's really "deferred it, and gave up our own
    play." In a prize-race game (Pokemon TCG's win condition IS trading KOs),
    this pattern is confidently wrong, not noise: it survives even a
    chunky-margin check (_meaningfully_better) since the horizon-hidden loss is
    a full prize, not an epsilon.

    Originally only guarded ATTACK->END/RETREAT (diagnosed via B2_DEBUG tracing
    against crustle). Re-traced against ex_lucario/dragapult/mirror and found
    the identical signature under PLAY->END and ABILITY->END too (e.g.
    declining to play a bench Pokemon "wins" a whole extra prize in the
    simulated continuation -- not a real strategic insight, an artifact of a
    single-sample, shallow simulated opponent reply) -- broadened to reject ANY
    override whose candidate is END. Then found it AGAIN as ATTACK->PLAY (not
    just ATTACK->END): base_v showed losing 3 whole prizes for attacking vs 0
    for playing a bench card instead, an implausible swing for "not attacking
    this turn". The real (base) policy already has real domain logic deciding
    whether/what to attack; every traced override AWAY from a real attack, to
    ANY alternative, has looked spurious -- so reject those wholesale rather
    than trust the search's shallow verdict on this specific class of choice."""
    ct = select.option[cand_idx].type
    if ct == api.OptionType.END:
        return True
    bt = select.option[base_idx].type
    if bt == api.OptionType.ATTACK and ct != api.OptionType.ATTACK:
        return True
    return False


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _card_ids(cards):
    return [c.id for c in cards or [] if c is not None and getattr(c, "id", None) is not None]


def _mon_ids(mons):
    out = []
    for m in mons or []:
        if m is None:
            continue
        out += _card_ids([m])
        out += _card_ids(getattr(m, "preEvolution", None))
        out += _card_ids(getattr(m, "energyCards", None) or [])
        out += _card_ids(getattr(m, "tools", None))
    return out


CFG = SearchConfig(
    depth=int(os.environ.get("B2_DEPTH", "2")),
    branch_single=int(os.environ.get("B2_BRANCH", "4")),
    opp_branch=int(os.environ.get("B2_OPP_BRANCH", "2")),
    probe_cap=int(os.environ.get("B2_PROBE_CAP", "4")),
    multi_alts=int(os.environ.get("B2_MULTI_ALTS", "1")),
    node_budget=int(os.environ.get("B2_BUDGET", "200")),
    branch_decisions_per_ply=int(os.environ.get("B2_PLY_DECISIONS", "2")),
    opp_mode=os.environ.get("B2_OPP_MODE", "minimax"),
    use_alpha_beta=os.environ.get("B2_AB", "1") == "1",
    eval_fn=default_eval if os.environ.get("B2_EVAL") == "default" else rich_eval,
    snapshot_fn=default_snapshot if os.environ.get("B2_EVAL") == "default" else rich_snapshot,
)
K = int(os.environ.get("B2_K", "1"))
STATS = {"planned": 0, "fired": 0, "errors": 0}


def make_agent(deck):
    base = P.make_agent(deck)
    roll = P.make_agent(deck)          # separate instance: our own move-ranking policy in search
    opp_model = OpponentModel(deck, P.make_agent)
    rng = random.Random(20260705)
    # Cumulative, monotonic per-card-id counts of what we've actually seen from
    # the opponent (board + discard) over the WHOLE game so far -- element-wise
    # max against each new observation, so a count we've verified never regresses
    # even if a later snapshot happens to show fewer (e.g. some recycling
    # effect). Recording this is the whole point of this pass: once the
    # archetype's exact 60-card list is known (opp_model.deck), subtracting what
    # we've actually seen from it gives an EXCLUSION-based hidden-info pool,
    # instead of the old heuristic of sampling WITH replacement from "cards
    # we've happened to see" -- which could invent a 2nd/3rd copy of a 1-of that
    # doesn't exist, manufacturing a phantom combo the opponent doesn't actually
    # have (diagnosed as a likely driver of the still-catastrophic dragapult/
    # archaludon results in exp038/SESSION_NOTES.md).
    seen_opp = Counter()
    # `run_gauntlet` reuses ONE agent callable (this whole closure) across MANY
    # games, and eval_b2.py's field battery reuses it across MANY DIFFERENT
    # opponent archetypes too. `obs.current.turn` is strictly non-decreasing
    # within one game and resets low at the start of the next -- use a regression
    # in it as the "new game started" signal to hard-reset seen_opp (and force
    # the opponent model to re-detect/rebuild) so a previous game's or a
    # previous DIFFERENT OPPONENT's cards never bleed into this game's exclusion
    # pool (which would otherwise silently subtract a stranger's deck from this
    # opponent's, or exhaust the pool over many games of the same opponent).
    _last_turn = [-1]

    def det(me, opp):
        rem = Counter(deck)
        rem.subtract(Counter(_card_ids(me.hand) + _mon_ids(me.active)
                             + _mon_ids(me.bench) + _card_ids(me.discard)))
        pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
        if len(pool) < me.deckCount + len(me.prize):
            pool = list(deck)
        rng.shuffle(pool)

        cur_opp = Counter(_mon_ids(opp.active) + _mon_ids(opp.bench) + _card_ids(opp.discard))
        for cid, cnt in cur_opp.items():
            if cnt > seen_opp[cid]:
                seen_opp[cid] = cnt
        active_unknown = len(opp.active) > 0 and opp.active[0] is None
        needed = opp.deckCount + len(opp.prize) + opp.handCount + (1 if active_unknown else 0)

        opool = None
        known_deck = opp_model.deck
        if known_deck:
            rem_opp = Counter(known_deck)
            rem_opp.subtract(seen_opp)
            cand = [cid for cid, cnt in rem_opp.items() for _ in range(max(cnt, 0))]
            if len(cand) >= needed:
                opool = cand
        if opool is not None:
            rng.shuffle(opool)
            c = 0
            def take(k):
                nonlocal c
                out = opool[c: c + k]
                c += k
                return out
            opp_deck_sel = take(opp.deckCount)
            opp_prize_sel = take(len(opp.prize))
            opp_hand_sel = take(opp.handCount)
            opp_active_sel = take(1) if active_unknown else []
        else:
            # fallback (archetype unknown / accounting didn't add up): the old
            # with-replacement heuristic over cards we've directly seen.
            fallback = _mon_ids(opp.active) + _mon_ids(opp.bench) + _card_ids(opp.discard)
            if not fallback:
                fallback = list(deck)
            samp = lambda k: [fallback[rng.randrange(len(fallback))] for _ in range(k)]
            opp_deck_sel = samp(opp.deckCount)
            opp_prize_sel = samp(len(opp.prize))
            opp_hand_sel = samp(opp.handCount)
            opp_active_sel = samp(1) if active_unknown else []

        return dict(your_deck=pool[: me.deckCount],
                    your_prize=pool[me.deckCount: me.deckCount + len(me.prize)],
                    opponent_deck=opp_deck_sel,
                    opponent_prize=opp_prize_sel,
                    opponent_hand=opp_hand_sel,
                    opponent_active=opp_active_sel)

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            return list(deck)
        cur_turn = obs.current.turn if obs.current is not None else None
        if cur_turn is not None and cur_turn < _last_turn[0]:
            seen_opp.clear()
            opp_model._archetype = None
            opp_model._agent = None
            opp_model.deck = None
        if cur_turn is not None:
            _last_turn[0] = cur_turn
        select = obs.select
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        if (select.maxCount != 1 or len(select.option) <= 1
                or select.context != api.SelectContext.MAIN):
            return base_sel
        # `roll` (my_policy for search rollouts) carries cross-turn state (the
        # revenge-window `_rev` tracker) that assumes a single chronological
        # playthrough. depth=2 search calls it across MANY hypothetical
        # branches spanning a turn boundary (our turn -> opponent's turn ->
        # possibly back), which corrupts that tracking (same bug class exp035's
        # tb_patch.py guards against for the shipped build, but the dev-time
        # revenge_policy instance here had no such protection). Snapshot/restore
        # around every search call so imagined branches never leak into either
        # (a) subsequent search calls in this same decision, or (b) roll's state
        # as seen by future REAL decisions.
        _rev_mod = getattr(roll, "_mod", None)
        if _rev_mod is not None:
            # BUG (found by tracing): the snapshot below must reflect roll's
            # cross-turn state AFTER observing the REAL current turn, or every
            # restore-to-snapshot at the end of this decision resets roll back
            # to whatever it was BEFORE this turn was ever seen -- since roll is
            # only ever invoked from inside search_best_action (never on the
            # bare real obs directly), _rev["turn"]/_rev["window"] would never
            # actually advance across real decisions, permanently freezing
            # roll's revenge-window detection at its initial value. Bootstrap
            # with one real call first so the snapshot captures the CORRECT
            # up-to-date value, matching what `base`'s own _rev would show.
            try:
                roll(obs_dict)
            except Exception:
                pass
        _rev_save = dict(_rev_mod.__dict__["_rev"]) if _rev_mod is not None else None
        my = obs.current.yourIndex
        opp_policy = opp_model.policy(obs)
        # Same class of bug, applied to the OPPONENT's archetype-matched pilot
        # instance: it is NEVER called on the real, chronological opponent turn
        # (that's decided by a totally separate agent instance owned by the
        # harness/environment) -- every call we make to it, at every decision
        # for the WHOLE game, is a hypothetical search call. Bootstrap with one
        # real-obs call so its cross-turn globals track the real game's
        # chronology as best they can (mirrors the roll/_rev fix above), then
        # snapshot/restore around every hypothetical use.
        opp_mod = getattr(opp_policy, "_mod", None)
        if opp_mod is not None:
            try:
                opp_policy(obs_dict)
            except Exception:
                pass
        opp_save = _snap_mod(opp_mod)
        try:
            STATS["planned"] += 1
            candidate = None
            for _ in range(K):
                if _rev_mod is not None:
                    _rev_mod.__dict__["_rev"].clear()
                    _rev_mod.__dict__["_rev"].update(_rev_save)
                _restore_mod(opp_mod, opp_save)
                me0 = obs.current.players[my]
                opp0 = obs.current.players[1 - my]
                d = det(me0, opp0)
                # ONE search_begin per iteration (one shared random world): the
                # candidate action and base's own action are scored from the
                # SAME tree, so the comparison is apples-to-apples (see
                # search_lib's must_include docstring on why a separate call
                # would silently compare two different random worlds).
                must = [base_sel[0]] + ([candidate] if candidate is not None else [])
                best_a, best_v, values = search_best_action(
                    api, obs, my, roll, opp_policy, CFG, d, must_include=must)
                base_v = values.get(base_sel[0])
                # NEG_INF is search_lib's "never evaluated" sentinel (budget
                # starved before this candidate's own first step) -- never a
                # real outcome. Treat it as unknown, same as None, so a
                # budget-starved base/candidate can't be spuriously "beaten".
                if base_v == NEG_INF:
                    base_v = None
                if candidate is None:
                    # first iteration: pick ONE specific candidate to verify
                    if (best_a is None or best_a == base_sel[0] or base_v is None
                            or best_v == NEG_INF or not _meaningfully_better(best_v, base_v)
                            or _is_horizon_dodge(select, base_sel[0], best_a)):
                        break
                    candidate = best_a
                else:
                    # later iterations: re-verify the SAME candidate (not
                    # whichever action happens to look best in this new world)
                    cand_v = values.get(candidate)
                    if cand_v == NEG_INF:
                        cand_v = None
                    if cand_v is None or base_v is None or not _meaningfully_better(cand_v, base_v):
                        candidate = None
                        break
            if candidate is not None:
                STATS["fired"] += 1
                if os.environ.get("B2_DEBUG"):
                    bo, co = select.option[base_sel[0]], select.option[candidate]
                    hand = obs.current.players[my].hand or []

                    def _card_name(o):
                        cid = o.cardId
                        if cid is None and o.type == api.OptionType.PLAY and o.index is not None and o.index < len(hand):
                            h = hand[o.index]
                            cid = h.id if h is not None else None
                        c = _all_cards.get(cid) if cid is not None else None
                        return f"{cid}:{getattr(c, 'name', '?')}" if cid is not None else "?"
                    print(f"FIRE turn={obs.current.turn} base={base_sel[0]}:type={api.OptionType(bo.type).name}:{_card_name(bo)} "
                          f"-> cand={candidate}:type={api.OptionType(co.type).name}:{_card_name(co)} "
                          f"base_v={base_v} cand_v={values.get(candidate)}",
                          file=sys.stderr)
                return [candidate]
        except Exception:
            STATS["errors"] += 1
            if os.environ.get("B2_DEBUG_ERR"):
                import traceback
                traceback.print_exc(file=sys.stderr)
        finally:
            if _rev_mod is not None:
                _rev_mod.__dict__["_rev"].clear()
                _rev_mod.__dict__["_rev"].update(_rev_save)
            _restore_mod(opp_mod, opp_save)
        return base_sel

    agent.__name__ = "beam2ply_ab"
    return agent
