"""exp039 — v014 turn-beam base + v013's opponent-reply doom-veto, upgraded with
exp038's archetype-matched opponent model for the reply rollout.

Context: v013's guard (exp029/guard_policy.py) already supports GUARD_BASE=turnbeam
(v014 as the base pilot) -- this combo was measured at n=200: total 2.61, BELOW
v014 alone (2.67). Per-matchup: crustle 0.870 (v014 alone: 0.905, -0.035), dragapult
0.160 (v014: 0.22, -0.06), archaludon 0.185 (v014: 0.195, -0.01), mirror_chq 0.620
(v014: 0.58, +0.04), ex_lucario 0.775 (v014: 0.77, ~flat). The guard HURT exactly
the matchups where the opponent runs a DIFFERENT deck (crustle/dragapult/archaludon)
and helped/held on mirror_chq (SAME deck) -- the fingerprint of a mismatched
opponent-reply simulation: guard_policy's `roll_opp` was plain revenge_policy (OUR
OWN deck's policy) pretending to be the opponent, exactly the flaw exp038's
opponent_model.py (archetype-matched real pilots + exclusion-based hidden-info
sampling) was built to fix.

This experiment keeps v013's PROVEN doom-veto criteria and K-loop UNCHANGED
(categorical doom levels: 2=we lose, 1=opponent takes >=2 prizes or our charged
attacker is wiped, 0=fine; override only when doomed in ALL K) -- exp038's own
continuous eval_fn + margin comparison design was tried and, even after 11 bug
fixes, did not beat baseline (see exp038/SESSION_NOTES.md). Only the OPPONENT
reply-rollout policy is swapped for the archetype-matched OpponentModel, plus the
state-contamination protections exp038 needed for reusing stateful policy
instances across many rollouts of the same chronological span (`roll_me`'s
revenge-window `_rev`, and the opponent pilot's own cross-turn globals).

Env: GUARD_K (4), GUARD_MAX_ALT (8), REVENGE_BONUS=50.
"""
from __future__ import annotations
import dataclasses
import os
import random
import sys
import types
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp019_finisher"),
          os.path.join(ROOT, "workspace", "exp023_revenge"),
          os.path.join(ROOT, "workspace", "exp035_turnbeam"),
          os.path.join(ROOT, "workspace", "exp038_beam2ply"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine  # noqa
import turnbeam_policy as P  # noqa  (v014 base pilot)
import revenge_policy as RVP  # noqa  (cheap rollout policy for OUR OWN continuation)
from opponent_model import OpponentModel  # noqa  (exp038 archetype-matched model)
from prize_tracker import PrizeTracker  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class

K = int(os.environ.get("GUARD_K", "4"))
MAX_ALT = int(os.environ.get("GUARD_MAX_ALT", "8"))
ROLL_CAP = 120
STATS = {"checked": 0, "doomed": 0, "fired": 0, "errors": 0}


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


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
        out += _card_ids(getattr(m, "energyCards", None) or getattr(m, "energies", None))
        out += _card_ids(getattr(m, "tools", None))
    return out


def _max_energy(player):
    best = 0
    for m in list(player.active or []) + list(player.bench or []):
        if m is None:
            continue
        e = getattr(m, "energyCards", None) or getattr(m, "energies", None) or []
        best = max(best, len(e))
    return best


def _snap_mod(mod):
    """Generic cross-turn-state snapshot (see exp038/beam2_policy.py's version):
    a stateful policy module assumes a single chronological playthrough, but here
    the SAME roll_me/opp_policy instances replay the SAME chronological span
    (this decision -> end of our turn -> end of opponent's reply) once per K
    iteration AND once per candidate option in the MAX_ALT loop -- without
    protection, iteration 2 would see state mutated by iteration 1's rollout
    instead of the true state as of this real decision."""
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


def make_agent(deck):
    base = P.make_agent(deck)
    roll_me = RVP.make_agent(deck)     # plays our seat inside the search (plain pilot)
    opp_model = OpponentModel(deck, RVP.make_agent)
    tracker = PrizeTracker(deck)
    rng = random.Random(20260702)
    seen_opp = Counter()               # cumulative opponent-card sightings (exp038 fix)
    _last_turn = [-1]                  # new-game detector (exp038 fix)

    def our_deck_sample(me):
        rem = Counter(deck)
        rem.subtract(Counter(_card_ids(me.hand) + _mon_ids(me.active) + _mon_ids(me.bench)
                             + _card_ids(me.discard)))
        pool = [cid for cid, cnt in rem.items() for _ in range(max(cnt, 0))]
        if len(pool) < me.deckCount + len(me.prize):
            pool = list(deck)
        rng.shuffle(pool)
        return pool[: me.deckCount], pool[me.deckCount: me.deckCount + len(me.prize)]

    def det(me, opp):
        d, prize = our_deck_sample(me)
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
            fallback = _mon_ids(opp.active) + _mon_ids(opp.bench) + _card_ids(opp.discard)
            if not fallback:
                fallback = list(deck)
            samp = lambda k: [fallback[rng.randrange(len(fallback))] for _ in range(k)]
            opp_deck_sel = samp(opp.deckCount)
            opp_prize_sel = samp(len(opp.prize))
            opp_hand_sel = samp(opp.handCount)
            opp_active_sel = samp(1) if active_unknown else []
        return dict(your_deck=d, your_prize=prize,
                    opponent_deck=opp_deck_sel, opponent_prize=opp_prize_sel,
                    opponent_hand=opp_hand_sel, opponent_active=opp_active_sel)

    def reply_outcome(obs, my, opt_i, opp_policy):
        """Apply opt_i, finish our turn, play the opponent's reply turn.
        Returns doom level: 2 = we lose, 1 = opp takes >=2 prizes or KOs our most-
        charged attacker, 0 = fine. None on rollout failure (treated as unknown)."""
        me0 = obs.current.players[my]
        opp0 = obs.current.players[1 - my]
        prizes0 = len(opp0.prize)
        charge0 = _max_energy(me0)
        ss = api.search_begin(obs, **det(me0, opp0))
        try:
            ss = api.search_step(ss.searchId, [opt_i])
            phase_opp_seen = False
            for _ in range(ROLL_CAP):
                o = ss.observation
                cur = o.current
                if cur is not None and cur.result != -1:
                    return 2 if cur.result == (1 - my) else 0
                if o.select is None or cur is None:
                    return None
                if cur.yourIndex == my:
                    if phase_opp_seen:
                        break
                    pol = roll_me
                else:
                    phase_opp_seen = True
                    pol = opp_policy
                ss = api.search_step(ss.searchId, _clamp(pol(dataclasses.asdict(o)), o.select))
            o = ss.observation
            if o.current is None:
                return None
            me1 = o.current.players[my]
            opp1 = o.current.players[1 - my]
            taken = prizes0 - len(opp1.prize)
            if taken >= 2:
                return 1
            if charge0 >= 2 and _max_energy(me1) < charge0 - 1:
                return 1
            return 0
        finally:
            try:
                api.search_release(ss.searchId)
            except Exception:
                try:
                    api.search_end()
                except Exception:
                    pass

    def doom_all_K(obs, my, opt_i, opp_policy, rev_mod, rev_save, opp_mod, opp_save):
        worst = 0
        for _ in range(K):
            if rev_mod is not None:
                rev_mod.__dict__["_rev"].clear()
                rev_mod.__dict__["_rev"].update(rev_save)
            _restore_mod(opp_mod, opp_save)
            d = reply_outcome(obs, my, opt_i, opp_policy)
            if d is None:
                return None
            if d == 0:
                return 0
            worst = max(worst, d)
        return worst

    def agent(obs_dict):
        obs = to_obs(obs_dict)
        if obs.select is None:
            tracker.reset()
            return list(deck)
        cur_turn = obs.current.turn if obs.current is not None else None
        if cur_turn is not None and cur_turn < _last_turn[0]:
            seen_opp.clear()
            opp_model._archetype = None
            opp_model._agent = None
            opp_model.deck = None
        if cur_turn is not None:
            _last_turn[0] = cur_turn
        try:
            tracker.update(obs)
        except Exception:
            pass
        select = obs.select
        try:
            base_sel = _clamp(base(obs_dict), select)
        except Exception:
            base_sel = _clamp([0], select)
        ctx = getattr(select, "context", None)
        if select.maxCount != 1 or len(select.option) <= 1 or ctx != api.SelectContext.MAIN:
            return base_sel
        my = obs.current.yourIndex
        opp_policy = opp_model.policy(obs)
        if opp_model._archetype == "Archaludon ex" and os.environ.get("GO_GATE_ARCH", "1") == "1":
            # archaludon regressed sharply (0.195 -> 0.10, n=100) even with the
            # archetype-matched opponent model -- already a structurally hard
            # matchup for us (exp025/026: HP300 + confirmed-KO 220dmg + non-ex
            # bypass), where most decisions may look "doomed" in some sense
            # regardless of the real tactical merit, making the categorical
            # veto fire on noise from the losing race itself rather than a
            # real mistake. Skip the guard entirely once detected; defer to
            # base (v014 turn-beam alone) for this matchup.
            return base_sel
        rev_mod = getattr(roll_me, "_mod", None)
        opp_mod = getattr(opp_policy, "_mod", None)
        # Bootstrap BOTH stateful instances with one real call on the actual
        # current obs before snapshotting, or the snapshot/restore cycle below
        # would freeze their cross-turn tracking at pre-this-turn state forever
        # (same bug found and fixed in exp038/beam2_policy.py).
        if rev_mod is not None:
            try:
                roll_me(obs_dict)
            except Exception:
                pass
        if opp_mod is not None:
            try:
                opp_policy(obs_dict)
            except Exception:
                pass
        rev_save = dict(rev_mod.__dict__["_rev"]) if rev_mod is not None else None
        opp_save = _snap_mod(opp_mod)
        try:
            STATS["checked"] += 1
            base_doom = doom_all_K(obs, my, base_sel[0], opp_policy, rev_mod, rev_save, opp_mod, opp_save)
            if not base_doom:
                return base_sel
            STATS["doomed"] += 1
            best = (base_doom, base_sel[0])
            for i in range(min(len(select.option), MAX_ALT)):
                if i == base_sel[0]:
                    continue
                d = doom_all_K(obs, my, i, opp_policy, rev_mod, rev_save, opp_mod, opp_save)
                if d is not None and d < best[0]:
                    best = (d, i)
                    if d == 0:
                        break
            if best[1] != base_sel[0]:
                STATS["fired"] += 1
                return [best[1]]
        except Exception:
            STATS["errors"] += 1
        finally:
            if rev_mod is not None:
                rev_mod.__dict__["_rev"].clear()
                rev_mod.__dict__["_rev"].update(rev_save)
            _restore_mod(opp_mod, opp_save)
        return base_sel

    agent.__name__ = "guard_opp_turnbeam"
    return agent
