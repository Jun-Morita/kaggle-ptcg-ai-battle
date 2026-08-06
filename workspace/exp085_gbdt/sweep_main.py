"""Sweep the ranker's capacity on the family that carries the errors.

main (SelectContext = -1) is 52% of all held-out mistakes and 45% of all
decisions, so it is where capacity is worth spending. It also stopped early at
271 of 600 rounds in the v4 run, which usually means the trees ran out of room
rather than out of signal -- num_leaves=63 over 284k training queries is thin.

Only `main` is fitted here: the other four families are cheap and already sit at
0.85-0.92, so sweeping them would spend hours to move the overall number by
hundredths. Reported metric is exact-set top-k on the held-out tail, the same one
train_gbdt.py prints, so numbers are directly comparable.

Usage: uv run python sweep_main.py [--rows v4] [--rounds 900]
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
import feats  # noqa: E402
from build_rows import arg  # noqa: E402
from train_gbdt import load, groups_from_qid, topk_accuracy  # noqa: E402

GRID = [
    dict(num_leaves=63,  learning_rate=0.08, min_data_in_leaf=40),   # v4 baseline
    dict(num_leaves=127, learning_rate=0.06, min_data_in_leaf=40),
    dict(num_leaves=255, learning_rate=0.05, min_data_in_leaf=60),
    dict(num_leaves=127, learning_rate=0.06, min_data_in_leaf=20),
    dict(num_leaves=511, learning_rate=0.04, min_data_in_leaf=100),
    dict(num_leaves=1023, learning_rate=0.035, min_data_in_leaf=150),
    dict(num_leaves=2047, learning_rate=0.03, min_data_in_leaf=200),
]


def main():
    tag = arg("--rows", "v4")
    rounds = int(arg("--rounds", "900"))
    data = load(tag)
    ctx, qid, y, X = data["main"]
    cat = [feats.IDX[n] for n in feats.CATEGORICAL]
    uq = np.unique(qid)
    cut = uq[int(len(uq) * 0.9)]
    tr, va = qid < cut, qid >= cut
    print(f"main: train_q {len(np.unique(qid[tr]))}  val_q {len(np.unique(qid[va]))}",
          flush=True)
    dtr = lgb.Dataset(X[tr], label=y[tr], group=groups_from_qid(qid[tr]),
                      categorical_feature=cat, free_raw_data=False)
    dva = lgb.Dataset(X[va], label=y[va], group=groups_from_qid(qid[va]),
                      categorical_feature=cat, reference=dtr, free_raw_data=False)
    best, rows = None, []
    for g in GRID:
        p = {"objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [1],
             "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
             "lambdarank_truncation_level": 12, "verbosity": -1, "seed": 42,
             "num_threads": 0, **g}
        t0 = time.time()
        bst = lgb.train(p, dtr, num_boost_round=rounds, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(60, verbose=False)])
        sc = bst.predict(X[va], num_iteration=bst.best_iteration)
        acc, n, _a1, _n1 = topk_accuracy(sc, y[va], qid[va])
        rows.append({**g, "topk": round(acc, 4), "trees": bst.best_iteration,
                     "sec": round(time.time() - t0)})
        print(f"  leaves {g['num_leaves']:>4} lr {g['learning_rate']:.3f} "
              f"min_leaf {g['min_data_in_leaf']:>3}  topk {acc:.4f}  "
              f"trees {bst.best_iteration}  ({time.time()-t0:.0f}s)", flush=True)
        if best is None or acc > best[0]:
            best = (acc, g, bst)
    print(f"\n  best: topk {best[0]:.4f}  {best[1]}")
    out = os.path.join(HERE, "results", f"sweep_main2_{tag}.json")
    json.dump({"tag": tag, "grid": rows, "best": best[1]}, open(out, "w"), indent=1)
    best[2].save_model(os.path.join(HERE, "results", f"sweep_main2_{tag}.txt"))
    print(f"  saved -> {out}")


if __name__ == "__main__":
    main()
