"""The shipped agent: score every legal option with the tree ensemble, take top-k.

Design constraints this has to satisfy, all learned from earlier submissions:
  no numpy          v015 crashed on `import numpy` in the sandbox
  no __file__       v015-fix4: Kaggle execs main.py's source, __file__ is undefined
  crash-safe        any exception must still return a LEGAL action, never raise
  fast per act      the 600s budget is per GAME; a few hundred tuple walks per
                    option is microseconds, so unlike the MCTS build there is no
                    time-budget machinery here at all

Deliberately NO search. The transformer build spends ~5x wall clock on MCTS for a
gain the ladder never confirmed, and the reference agent reaches a comparable score
with a pure feed-forward ranker. If search is worth adding back it should be added
against a measured baseline, not assumed.

Contexts with no fitted family fall through to `easy`, and a decision with fewer
than 2 options is answered without scoring anything.
"""
from __future__ import annotations
import os
import pickle

_FALLBACK_FAM = "easy"


def load_pure(path):
    with open(path, "rb") as f:
        blob = pickle.load(f)
    ctx2fam = {}
    for fam, ids in blob["family"].items():
        for c in ids:
            ctx2fam[int(c)] = fam
    blob["ctx2fam"] = ctx2fam
    return blob


def score_rows(pure, fam, rows):
    """Sum of leaf values over the family's trees, one score per row."""
    trees = pure["models"].get(fam) or pure["models"].get(_FALLBACK_FAM) or []
    out = []
    for row in rows:
        total = 0.0
        for left, right, feat, thr, cats, val in trees:
            i = 0
            while True:
                f = feat[i]
                if f < 0:
                    total += val[i]
                    break
                t = thr[i]
                if t is None:
                    i = left[i] if int(row[f]) in cats[i] else right[i]
                else:
                    i = left[i] if row[f] <= t else right[i]
        out.append(total)
    return out


def make_agent(pure_path, deck):
    """Returns agent(obs_dict) -> list[int]; never raises.

    `fallbacks` counts decisions answered by the except branch rather than by the
    model. It exists because that branch is silent by design -- it returns a LEGAL
    move, so a broken agent shows up as a normal-looking 0-25 record with zero
    reported errors, not as a crash. Three separate bugs hid there this session
    (load_ref's lazy import, feats' train_mcts import, and the build's stripped
    `import feats`). build_submission.smoke() asserts this stays 0.
    """
    import feats as _feats
    from cg.api import to_observation_class

    pure = load_pure(pure_path)
    state = {"history": [], "fallbacks": 0, "decisions": 0}
    option_rows = _feats.option_rows

    def agent(obs_dict):
        try:
            sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
            if sel is None:
                state["history"] = []
                return list(deck)
            n_opt = len(sel.get("option") or [])
            lo = int(sel.get("minCount", 0) or 0)
            hi = min(n_opt, int(sel.get("maxCount", 0) or 0))
            if n_opt == 0 or hi <= 0:
                return []
            state["decisions"] += 1
            oc = to_observation_class(obs_dict)
            rows, sems = option_rows(oc, state["history"])
            ctx = int(getattr(oc.select, "context", -1) or -1)
            fam = pure["ctx2fam"].get(ctx, _FALLBACK_FAM)
            sc = score_rows(pure, fam, rows)
            order = sorted(range(n_opt), key=lambda i: (-sc[i], i))
            k = max(lo, min(hi, hi))
            chosen = sorted(order[:k])
            turn = oc.current.turn
            for i in chosen:
                state["history"].append((turn, sems[i]))
            state["history"] = state["history"][-40:]
            return chosen
        except Exception:
            state["fallbacks"] += 1
            try:
                sel = obs_dict.get("select") or {}
                n_opt = len(sel.get("option") or [])
                lo = int(sel.get("minCount", 0) or 0)
                return list(range(min(n_opt, max(lo, 1))))
            except Exception:
                return [0]

    agent.state = state
    return agent
