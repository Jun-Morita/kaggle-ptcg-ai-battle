"""Fit the position evaluator that search will consume.

Binary classification (this seat eventually won) over the same flat state
features the ranker uses, minus the per-option columns -- those describe a choice,
not a position, and are zero here by construction.

Two honest caveats about the training distribution, recorded because they bound
what the value head can be trusted for:

  seat selection. Rows come from games where at least one seat ran our exact 60
  cards and was indexed as a teacher (top-band, winning). Losing rows therefore
  come disproportionately from MIRROR games, where both seats hold our deck. The
  model sees far fewer "our deck losing to Alakazam" positions than the ladder
  will show it.

  outcome, not value. The label is the game result, so an even position played on
  by a strong pilot is labelled 1. That inflates confidence in positions that were
  merely recoverable. Search only needs a ranking between sibling positions, which
  survives a monotone distortion, but the absolute number is not a win probability.

Reported: AUC and accuracy on a held-out tail, plus the base rate, because with a
~74% win base rate accuracy alone would look good while learning nothing.

Usage: uv run python train_value.py [--rows v1] [--rounds 500]
"""
from __future__ import annotations
import json, os, pickle, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
import feats  # noqa: E402
from build_rows import arg  # noqa: E402

# option-level columns carry no information about a POSITION
OPT_PREFIXES = ("opt_", "src_", "tgt_", "dup_")


def load(tag):
    path = os.path.join(HERE, "results", f"value_{tag}.pkl")
    Ys, Xs = [], []
    with open(path, "rb") as f:
        while True:
            try:
                y, X = pickle.load(f)
            except EOFError:
                break
            Ys.append(y); Xs.append(X)
    return np.concatenate(Ys), np.concatenate(Xs)


def main():
    tag = arg("--rows", "v1")
    rounds = int(arg("--rounds", "500"))
    y, X = load(tag)
    keep = [i for i, n in enumerate(feats.FEATURES)
            if not n.startswith(OPT_PREFIXES) or n.startswith("opt_type_count_")]
    cat = [k for k, i in enumerate(keep)
           if feats.FEATURES[i] in feats.CATEGORICAL]
    Xk = X[:, keep]
    cut = int(len(y) * 0.9)
    tr, va = slice(0, cut), slice(cut, len(y))
    base = float(y[va].mean())
    dtr = lgb.Dataset(Xk[tr], label=y[tr], categorical_feature=cat, free_raw_data=False)
    dva = lgb.Dataset(Xk[va], label=y[va], categorical_feature=cat, reference=dtr,
                      free_raw_data=False)
    params = {"objective": "binary", "metric": "auc", "learning_rate": 0.06,
              "num_leaves": 63, "min_data_in_leaf": 80, "feature_fraction": 0.8,
              "bagging_fraction": 0.8, "bagging_freq": 1, "verbosity": -1,
              "seed": 42, "num_threads": 0}
    t0 = time.time()
    bst = lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva],
                    callbacks=[lgb.early_stopping(40, verbose=False)])
    p = bst.predict(Xk[va], num_iteration=bst.best_iteration)
    order = np.argsort(p)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(p))
    pos, neg = y[va] == 1, y[va] == 0
    auc = (ranks[pos].mean() - (pos.sum() - 1) / 2) / max(1, neg.sum())
    acc = float(((p >= 0.5) == (y[va] == 1)).mean())
    print(f"  rows {len(y)} (win base rate {float(y.mean()):.3f})  "
          f"val {int(va.stop - va.start)}  base {base:.3f}")
    print(f"  AUC {auc:.4f}   acc {acc:.4f}   trees {bst.best_iteration} "
          f"({time.time()-t0:.0f}s)")
    out = os.path.join(HERE, "results", f"value_{tag}")
    os.makedirs(out, exist_ok=True)
    bst.save_model(os.path.join(out, "value.txt"))
    json.dump({"tag": tag, "rows": int(len(y)), "auc": round(float(auc), 4),
               "acc": round(acc, 4), "trees": bst.best_iteration,
               "keep": [feats.FEATURES[i] for i in keep]},
              open(os.path.join(out, "report.json"), "w"), indent=1)
    print(f"  saved -> {out}")


if __name__ == "__main__":
    main()
