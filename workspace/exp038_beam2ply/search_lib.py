"""exp038 — general N-ply determinized alpha-beta search over the cabt engine's
forward-search API. Generalizes exp035's single-turn beam (depth=1, MAX-only) and
exp029's opponent-reply guard (depth=2, opponent modeled by a fixed cheap policy)
into one configurable primitive.

Design points (see workspace/exp038_beam2ply/SESSION_NOTES.md for the review that
motivated each one):

1. MULTI-SELECT decisions (select.maxCount > 1): engine source review (SelectProc/
   EffectProc/SetupProc.h: selectMax defaults to 1, and is only raised for specific,
   fixed-selectCount effects — bench setup, "discard up to N", etc. — not a
   pervasive per-turn thing). We delegate these to a real policy (never a naive
   `range(minCount)` default) and, when budget allows, explore a few "swap one
   card" neighbor alternates — full combinatorial branching (choose k of n) is
   exponential and not attempted; empirically low-value given how few/simple
   real multi-select decisions are.

2. ARBITRARY DEPTH: `depth` counts ply = turn-transitions (depth=1 -> our current
   turn only == exp035; depth=2 -> + the opponent's reply == exp029/38; ...).

3. TWO SEPARATE POLICIES for move ranking/continuation: `my_policy` (ours) and
   `opp_policy` (the OPPONENT's). Using OUR OWN deck's policy to guess what e.g. an
   Archaludon or Dragapult pilot would do is a mismatch (their scoring depends on
   THEIR cards); callers should supply an archetype-matched policy for opp_policy
   when known (see opponent_model.py), falling back to a generic one otherwise.

4. PROBE-BASED MOVE ORDERING: rather than trusting only a static policy's
   preference, every deduped candidate at a single-select node is given a cheap
   ONE-STEP probe (a single `search_step` + `eval_fn` on the resulting state, no
   recursion) and candidates are ranked by that real simulated outcome before
   deciding which get full recursive deepening. This (a) is a stronger ordering
   signal than a static heuristic since it reflects the engine's actual result,
   and (b) directly improves alpha-beta efficiency (better ordering -> more
   cutoffs for the same node budget). Probed children are reused as the
   recursion's starting point (no re-stepping).

5. ALPHA-BETA PRUNING: our nodes maximize, the opponent's minimize, over a
   SYMMETRIC eval — cutoffs applied during the ranked-candidate loop.

6. Evaluation is PLUGGABLE (`cfg.eval_fn`, default `default_eval` = symmetric
   (prize_margin, hp_margin)); callers can supply a richer one (e.g. adding a
   "threat removed" term — see beam2_policy.py) without touching this module.

This module holds NO game/deck-specific logic beyond the default eval.
"""
from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from typing import Callable, Optional


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def _option_key(api, opt):
    """Identity key for an Option: two option-list slots that represent the same
    REAL choice (e.g. two hand slots holding identical card copies) collapse to
    the same key, so branching explores distinct strategic choices, not
    mechanically-identical duplicates. Board-position choices (attach/switch
    target on a specific bench slot) are kept distinct even for the same species,
    since e.g. two benched Phantump can differ in energy count / readiness."""
    is_hand_card = (getattr(opt, "area", None) == api.AreaType.HAND
                     and getattr(opt, "inPlayIndex", None) is None
                     and getattr(opt, "inPlayArea", None) is None)
    if is_hand_card:
        return ("hand", opt.type, opt.cardId, opt.toolIndex, opt.energyIndex,
                opt.number, opt.specialConditionType)
    return ("full", opt.type, opt.cardId, opt.attackId, opt.area, opt.index,
            opt.inPlayArea, opt.inPlayIndex, opt.playerIndex, opt.toolIndex,
            opt.energyIndex, opt.number, opt.specialConditionType)


def _dedup_indices(api, select, pref):
    """All option indices, deduped by real identity, `pref` entries first."""
    seen, out = set(), []

    def add(i):
        if i is None or not (0 <= i < len(select.option)):
            return
        key = _option_key(api, select.option[i])
        if key in seen:
            return
        seen.add(key)
        out.append(i)

    for i in pref:
        add(i)
    for i in range(len(select.option)):
        add(i)
    return out


def _neighbor_multiselects(base_sel, n_options, max_alts):
    """Up to max_alts alternates of a multi-select: swap ONE chosen index for an
    unchosen one (cheap local perturbation, not full enumeration)."""
    alts = []
    chosen = set(base_sel)
    unchosen = [i for i in range(n_options) if i not in chosen]
    for i in range(len(base_sel)):
        for u in unchosen:
            if len(alts) >= max_alts:
                return alts
            alt = list(base_sel)
            alt[i] = u
            alts.append(alt)
    return alts


@dataclass
class SearchConfig:
    depth: int = 1              # ply to explore (1 = our turn only, 2 = + opp reply, ...)
    branch_single: int = 10     # candidates kept (post-probe-ranking) at our maxCount==1 nodes
    opp_branch: int = 4         # candidates kept at the opponent's maxCount==1 nodes (minimax mode)
    probe_cap: int = 16         # max deduped candidates cheaply probed before ranking/capping
    multi_alts: int = 2         # max neighbor alternates generated at OUR multi-select nodes
    node_budget: int = 1500     # total search_step calls, shared across the whole tree
    branch_decisions_per_ply: int = 3  # branch/probe at only the first N decisions of
                                        # EACH ply; subsequent decisions in that same ply
                                        # just follow the single-best (pref) choice — caps
                                        # the worst case to branch^N instead of branch^(turn length)
    opp_mode: str = "policy"    # "policy" (single opp_policy child) or "minimax" (probe+expand+min)
    use_alpha_beta: bool = True
    eval_fn: Optional[Callable] = None       # (cur, my, base_snapshot) -> orderable tuple; higher=better for `my`
    snapshot_fn: Optional[Callable] = None   # (cur0, my) -> dict baseline for eval_fn; default tracks prize/hp


class _Budget:
    __slots__ = ("left",)

    def __init__(self, n):
        self.left = n

    def take(self):
        if self.left <= 0:
            return False
        self.left -= 1
        return True


def _board_hp(p):
    tot = 0
    for m in list(p.active or []) + list(p.bench or []):
        if m is not None:
            tot += getattr(m, "hp", 0) or 0
    return tot


def default_snapshot(cur0, my):
    return {"opp_prize": len(cur0.players[1 - my].prize), "my_prize": len(cur0.players[my].prize),
            "opp_hp": _board_hp(cur0.players[1 - my]), "my_hp": _board_hp(cur0.players[my])}


def default_eval(cur, my, base):
    """Symmetric (prize_margin, hp_margin) tuple, higher = better for `my`."""
    if cur is None:
        return (-1e9, 0.0)
    me, opp = cur.players[my], cur.players[1 - my]
    pm = ((base["opp_prize"] - len(opp.prize)) - (base["my_prize"] - len(me.prize)))
    hm = ((base["opp_hp"] - _board_hp(opp)) - (base["my_hp"] - _board_hp(me)))
    if cur.result == my:
        return (1e6 + pm, hm)
    if cur.result not in (-1, my):
        return (-1e6 + pm, hm)
    return (float(pm), float(hm))


NEG_INF = (-1e18, -1e18)
POS_INF = (1e18, 1e18)


def search_best_action(api, obs, my, my_policy, opp_policy, cfg: SearchConfig,
                        det_kwargs, must_include=None):
    """Run ONE determinization (one `api.search_begin` call, one shared random
    world) of the configured alpha-beta search from `obs` (a decision belonging
    to `my`). Returns (best_action, best_value, values) where `values` is a dict
    {action_index: value} for every root-level candidate actually explored (a
    superset of `must_include`, when the root is single-select — always None-safe
    otherwise). `det_kwargs`: dict for api.search_begin (your_deck/your_prize/
    opponent_*).

    IMPORTANT: `must_include` guarantees specific action indices (e.g. a base
    policy's own pick) are explored and scored FROM THIS SAME ROOT alongside the
    search's own candidates — comparing a candidate's value against a value
    computed from a SEPARATE `search_begin` call would silently compare two
    different random worlds if the engine's own RNG (coin flips, draw order
    beyond the supplied hidden-info lists) isn't reproduced call-to-call, which
    would make any resulting "verified better" comparison meaningless. Always
    compare values that came from the same `values` dict of the same call.
    """
    eval_fn = cfg.eval_fn or default_eval
    snapshot_fn = cfg.snapshot_fn or default_snapshot
    root = api.search_begin(obs, **det_kwargs)
    budget = _Budget(cfg.node_budget)
    cur0 = obs.current
    base = snapshot_fn(cur0, my)

    def _step(ss, sel):
        if not budget.take():
            return None
        try:
            return api.search_step(ss.searchId, sel)
        except Exception:
            return None

    def _policy_sel(o, owner):
        pol = my_policy if owner == my else opp_policy
        try:
            sel = pol(dataclasses.asdict(o))
        except Exception:
            sel = [0]
        return _clamp(sel, o.select)

    def _eval_of(ss):
        return eval_fn(ss.observation.current, my, base) if ss is not None else NEG_INF

    def play_ply(ss, plies_remaining, first_action, alpha, beta):
        o = ss.observation
        cur = o.current
        if cur is None or cur.result != -1 or o.select is None:
            return eval_fn(cur, my, base), first_action
        owner = cur.yourIndex
        counter = {"n": 0}   # fresh per-ply branch-decision counter (caps worst-case cost)
        if plies_remaining <= 1:
            return _walk_single_ply(ss, first_action, owner, alpha, beta, counter, continuation=None)
        return _walk_single_ply(ss, first_action, owner, alpha, beta, counter,
                                continuation=lambda ss2, fa2, a2, b2:
                                play_ply(ss2, plies_remaining - 1, fa2, a2, b2))

    def _walk_single_ply(ss, first_action, owner, alpha, beta, counter, continuation=None):
        o = ss.observation
        cur = o.current
        if (cur is None or cur.result != -1 or o.select is None
                or len(o.select.option) == 0):
            # An empty option list is a genuine (if rare) engine state, not
            # necessarily terminal -- but with nothing to select, `pref[0]`
            # below would IndexError. Evaluate in place rather than crash
            # (observed against archaludon's real 3rd-party pilot).
            return eval_fn(cur, my, base), first_action
        if cur.yourIndex != owner:
            if continuation is not None:
                return continuation(ss, first_action, alpha, beta)
            return eval_fn(cur, my, base), first_action
        is_ours = (owner == my)
        may_branch = counter["n"] < cfg.branch_decisions_per_ply

        def recurse_child(child, fa):
            return _walk_single_ply(child, fa, owner, alpha, beta, counter, continuation)

        maxc = o.select.maxCount
        if maxc != 1:
            base_sel = _policy_sel(o, owner)
            children_sels = [base_sel]
            if may_branch:
                n_alt = (cfg.multi_alts if is_ours
                         else (max(0, min(cfg.opp_branch - 1, 2)) if cfg.opp_mode == "minimax" else 0))
                children_sels += _neighbor_multiselects(base_sel, len(o.select.option), n_alt)
                counter["n"] += 1
            best_val, best_fa = None, first_action
            for sel in children_sels:
                child = _step(ss, sel)
                if child is None:
                    continue
                fa = first_action if first_action is not None else tuple(sel)
                v, ffa = recurse_child(child, fa)
                if best_val is None or (v > best_val if is_ours else v < best_val):
                    best_val, best_fa = v, ffa
                if cfg.use_alpha_beta:
                    if is_ours:
                        alpha = max(alpha, best_val)
                    else:
                        beta = min(beta, best_val)
                    if alpha >= beta:
                        break
            if best_val is None:
                return eval_fn(cur, my, base), first_action
            return best_val, best_fa

        # single-select (maxCount==1, but minCount may be 0 -- e.g. "you may
        # attach an energy" -- so `pref` legitimately can be [] as well as a
        # single index; _clamp already caps it to at most one entry either way)
        pref = _policy_sel(o, owner)
        pref_action = pref[0] if pref else "decline"
        if not may_branch or (not is_ours and cfg.opp_mode != "minimax"):
            # cheap mode: single child, the real policy's own choice — either
            # because opp_mode=="policy", or this ply already used up its
            # branch_decisions_per_ply budget (cap worst-case cost per ply)
            child = _step(ss, pref)
            if child is None:
                return eval_fn(cur, my, base), first_action
            fa = first_action if first_action is not None else pref_action
            return recurse_child(child, fa)
        counter["n"] += 1

        # PROBE-BASED MOVE ORDERING: cheaply step every deduped candidate once
        # (no recursion) and rank by the resulting state's eval — a stronger,
        # simulator-grounded ordering than a static heuristic, which also makes
        # the alpha-beta cutoffs below more effective. pref is included in the
        # dedup list (no special-casing needed) so it's naturally considered.
        cap = cfg.branch_single if is_ours else cfg.opp_branch
        dedup = _dedup_indices(api, o.select, pref)
        probed = []
        for i in dedup[: max(cfg.probe_cap, cap)]:
            child = _step(ss, [i])
            if child is None:
                continue
            probed.append((i, child, _eval_of(child)))
        # best-first for us (we maximize); most-dangerous-to-us-first for the
        # opponent (they minimize our eval) — either way, tightens alpha/beta fastest.
        probed.sort(key=lambda t: t[2], reverse=is_ours)

        best_val, best_fa = None, first_action
        for i, child, _pv in probed[:cap]:
            fa = first_action if first_action is not None else i
            v, ffa = recurse_child(child, fa)
            if best_val is None or (v > best_val if is_ours else v < best_val):
                best_val, best_fa = v, ffa
            if cfg.use_alpha_beta:
                if is_ours:
                    alpha = max(alpha, best_val)
                else:
                    beta = min(beta, best_val)
                if alpha >= beta:
                    break
        if best_val is None:
            return eval_fn(cur, my, base), first_action
        return best_val, best_fa

    def _play_from(child, forced_action):
        if child is None:
            return NEG_INF
        child_cur = child.observation.current
        child_owner = child_cur.yourIndex if child_cur is not None else my
        remaining = cfg.depth if child_owner == my else max(1, cfg.depth - 1)
        v, _fa = play_ply(child, remaining, forced_action, NEG_INF, POS_INF)
        return v

    try:
        o0 = root.observation
        must = list(must_include or [])
        if o0.select is not None and o0.select.maxCount == 1 and len(o0.select.option) > 1:
            # ROOT candidates are all explored from this ONE shared search_begin
            # (one determinization/RNG world) so their values are directly
            # comparable — evaluating a candidate via a SEPARATE search_begin
            # call (even with identical det_kwargs) would compare different
            # random worlds if the engine's own RNG (coin flips, draw order
            # beyond what we specify) isn't reproduced call-to-call.
            # `must` FIRST: with a shared node_budget across the whole tree, a
            # candidate evaluated late can find _step(root, [i]) starved (budget
            # already spent by earlier candidates' subtrees), returning NEG_INF
            # via _play_from(None, ...) -- a "never evaluated" sentinel, not a
            # real bad outcome. must_include (esp. the real base policy's own
            # action) MUST be evaluated while budget is fresh, or a candidate
            # that merely got lucky with budget looks "verified better than
            # NEG_INF" and fires spuriously on every such starvation.
            pref0 = _policy_sel(o0, my)
            cand0 = list(dict.fromkeys(must + _dedup_indices(api, o0.select, pref0)
                                       [: max(cfg.probe_cap, cfg.branch_single)]))
            values = {}
            best_a, best_v = None, None
            # EQUAL budget share per root candidate: a single shared _Budget
            # depleted sequentially across candidates biases the comparison --
            # whichever candidate is scored first (or gets lucky) explores
            # deeper/more-completely (sees the opponent's real response), while
            # later/unlucky candidates get truncated subtrees that fall back to
            # an optimistic eval_fn on an UNRESOLVED position (before the
            # opponent's reply is simulated) -- an apples-to-oranges search
            # DEPTH bias on top of the world/state ones already fixed.
            per_cand_budget = max(1, cfg.node_budget // max(1, len(cand0)))
            for i in cand0:
                if not (0 <= i < len(o0.select.option)):
                    continue
                budget = _Budget(per_cand_budget)
                v = _play_from(_step(root, [i]), i)
                values[i] = v
                if best_v is None or v > best_v:
                    best_v, best_a = v, i
            return best_a, best_v, values
        # multi-select (or single-option) root: no per-index comparison possible
        value, first_action = play_ply(root, cfg.depth, None, NEG_INF, POS_INF)
        return first_action, value, ({first_action: value} if first_action is not None else {})
    finally:
        try:
            api.search_end()
        except Exception:
            pass
