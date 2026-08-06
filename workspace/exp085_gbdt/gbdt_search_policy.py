"""Agent = GBDT ranker + verified-override search, sharing one scoring path.

Kept separate from gbdt_policy.make_agent so the A/B is honest: the search arm and
the no-search arm call the SAME score_options() over the SAME model, and differ
only in whether search.choose gets to look ahead. Anything else (a second feature
path, a second history window) would confound the one thing being measured.

The value model is a LightGBM booster here. If search proves out, it gets the same
pure-Python export treatment as the ranker before anything ships -- the artifact,
not the dev module, is what the gates measure.
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import feats  # noqa: E402  (loads engine)
import search as SEARCH  # noqa: E402
from gbdt_policy import load_pure, score_rows  # noqa: E402
from cg.api import to_observation_class  # noqa: E402


def load_value(path):
    import lightgbm as lgb
    import json
    bst = lgb.Booster(model_file=os.path.join(path, "value.txt"))
    keep_names = json.load(open(os.path.join(path, "report.json")))["keep"]
    keep = [feats.IDX[n] for n in keep_names]
    return bst, keep


def make_agent(pure_path, value_path, deck, use_search=True):
    """agent(obs_dict) -> list[int]; never raises. `state` carries the fallback
    counter so a gate can assert the model actually answered."""
    pure = load_pure(pure_path)
    bst, keep = load_value(value_path) if value_path else (None, None)
    state = {"history": [], "fallbacks": 0, "decisions": 0,
             "searched": 0, "overrides": 0}

    def score_options(oc):
        rows, sems = feats.option_rows(oc, state["history"])
        ctx = int(getattr(oc.select, "context", -1) or -1)
        fam = pure["ctx2fam"].get(ctx, "easy")
        return score_rows(pure, fam, rows), sems

    def value_of(oc, our_index):
        """P(our seat wins). base_state is built from the perspective of the seat
        TO MOVE, which after a finished turn is the opponent -- so the raw score
        must be flipped when the position is not ours."""
        if bst is None:
            return 0.5
        row = feats.base_state(oc, state["history"])
        v = float(bst.predict([[row[i] for i in keep]])[0])
        return v if oc.current.yourIndex == our_index else 1.0 - v

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
            if use_search and bst is not None:
                act, info = SEARCH.choose(obs_dict, deck, score_options, value_of)
                state["searched"] += bool(info.get("searched"))
                state["overrides"] += bool(info.get("override"))
            else:
                sc, _ = score_options(oc)
                act = SEARCH.top_k(sc, max(lo, hi) or 1)
            _, sems = score_options(oc)
            turn = oc.current.turn
            for i in act:
                if 0 <= i < len(sems):
                    state["history"].append((turn, sems[i]))
            state["history"] = state["history"][-40:]
            return sorted(act)
        except Exception:
            state["fallbacks"] += 1
            try:
                sel = obs_dict.get("select") or {}
                n = len(sel.get("option") or [])
                lo = int(sel.get("minCount", 0) or 0)
                return list(range(min(n, max(lo, 1))))
            except Exception:
                return [0]

    agent.state = state
    return agent
