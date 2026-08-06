"""One-ply verified override: play the turn out, evaluate, override only on upside.

Why not MCTS. The transformer line has a working PUCT tree, and porting it to sit
on top of the GBDT would mean re-implementing node expansion, determinization
bookkeeping and backprop in the shipped file. Three separate silent-degradation
bugs turned up in this experiment alone (each returned a LEGAL move and reported
zero errors), and a tree is a much larger surface for a fourth. The design below
is the one that actually shipped and worked here before -- v013's upside-only
gate and v014's turn beam: keep the policy in charge, look ahead only to CHECK it,
and change the answer only when the alternative is verifiably better.

What it does, per decision:

  1. score every legal option with the ranker; the policy answer is the top-k set
  2. build a few sibling candidates by swapping in the next-best options
  3. for each candidate, in a determinized fork: apply it, then keep playing OUR
     side greedily with the same ranker until the turn leaves us or the game ends
  4. evaluate the resulting position with the value model
  5. take the best candidate only if it beats the policy answer by MARGIN

Averaged over DETS determinizations, because the uncertainty in this game lives in
the opponent's hidden cards, not in depth -- exp083 measured sc16 -> sc32 as worth
nothing (0.450, z=-0.89) while no-search -> sc16 was worth +0.325.

Cost: CANDS * DETS * (turn length) ranker calls, ~80 per decision, ~0.1s. The game
budget is 600s, so this is not close to the limit.
"""
from __future__ import annotations
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2"):
    if os.path.join(WS, p) not in sys.path:
        sys.path.insert(0, os.path.join(WS, p))

import feats  # noqa: E402  (loads engine)
from cg.api import search_begin, search_end, search_step, to_observation_class  # noqa: E402
from determinize import determinize  # noqa: E402
import train_mcts as _tm  # noqa: E402  POKEMON_IDS only

CANDS = int(os.environ.get("SEARCH_CANDS", "4"))
DETS = int(os.environ.get("SEARCH_DETS", "2"))
MARGIN = float(os.environ.get("SEARCH_MARGIN", "0.02"))
MAX_TURN_STEPS = int(os.environ.get("SEARCH_MAX_STEPS", "24"))


def top_k(scores, k):
    return sorted(sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k])


def candidates(scores, lo, hi, n_opt, limit=CANDS):
    """The policy answer, then single-substitution siblings of it.

    Deliberately NOT the full combination set: enumerating subsets is what makes
    the action space explode, and DeNA's Pokemon TCG Pocket writeup reports the
    same fix we use here -- keep actions atomic and generate a handful of concrete
    alternatives instead.
    """
    k = max(lo, min(hi, hi)) or 1
    order = sorted(range(n_opt), key=lambda i: (-scores[i], i))
    best = sorted(order[:k])
    out = [best]
    worst_in = min(best, key=lambda i: scores[i])
    for j in order[k:]:
        alt = sorted([i for i in best if i != worst_in] + [j])
        if alt not in out:
            out.append(alt)
        if len(out) >= limit:
            break
    return out


def _greedy_finish(state, our_index, score_options, value_of):
    """Play OUR side greedily from `state` until the turn leaves us or it ends."""
    steps = 0
    while steps < MAX_TURN_STEPS:
        obs = state.observation
        if obs.current.result >= 0:
            return 1.0 if obs.current.result == our_index else 0.0
        if obs.current.yourIndex != our_index:
            break
        if obs.select is None or not obs.select.option:
            break
        sc, _ = score_options(obs)
        lo = int(obs.select.minCount or 0)
        hi = min(len(obs.select.option), int(obs.select.maxCount or 0))
        sel = top_k(sc, max(lo, hi) or 1)
        try:
            state = search_step(state.searchId, sel)
        except Exception:
            break
        steps += 1
    return value_of(state.observation)


def choose(obs_dict, deck, score_options, value_of, rng=None):
    """Return (action, info). `score_options(obs_class) -> (scores, semantics)`;
    `value_of(obs_class) -> float in [0,1]` from OUR seat's point of view."""
    obs = to_observation_class(obs_dict)
    sel = obs.select
    n_opt = len(sel.option or [])
    lo = int(sel.minCount or 0)
    hi = min(n_opt, int(sel.maxCount or 0))
    scores, _sems = score_options(obs)
    policy_action = top_k(scores, max(lo, hi) or 1)
    if n_opt < 2 or hi <= 0:
        return policy_action, {"searched": 0}

    cands = candidates(scores, lo, hi, n_opt)
    if len(cands) < 2:
        return policy_action, {"searched": 0}

    our = obs.current.yourIndex
    totals = [0.0] * len(cands)
    runs = 0
    for _d in range(max(1, DETS)):
        try:
            kw = determinize(obs, our, list(deck), list(deck), _tm.POKEMON_IDS, rng=rng)
        except Exception:
            break
        for ci, act in enumerate(cands):
            try:
                st = search_begin(obs, **kw)
                st = search_step(st.searchId, act)
                totals[ci] += _greedy_finish(st, our, score_options, value_of)
            except Exception:
                totals[ci] += 0.5          # unknown, not a reason to prefer or avoid
            finally:
                try:
                    search_end()
                except Exception:
                    pass
        runs += 1
    if not runs:
        return policy_action, {"searched": 0}

    vals = [t / runs for t in totals]
    base = vals[0]                          # cands[0] IS the policy answer
    bi = max(range(len(vals)), key=lambda i: vals[i])
    if bi != 0 and vals[bi] - base >= MARGIN:
        return cands[bi], {"searched": runs, "override": True,
                           "gain": vals[bi] - base}
    return policy_action, {"searched": runs, "override": False}
