"""Fit one LambdaRank model per SelectContext family and report top-k accuracy.

Why ranking and not classification. The agent consumes the model exactly one way:
score every legal option, take the top maxCount. So the training objective should
be "put the teacher's picks on top", which is what LambdaRank optimises directly.
A per-option binary classifier optimises calibrated probability instead, which we
never use, and a softmax over options cannot express a multi-select answer at all.

Why per-context models. A TO_HAND search decision and a damage-counter placement
share almost no signal; forcing one tree ensemble to serve both spends its early
splits separating the contexts instead of deciding within them. The families below
come from the counts our own corpus produced (see rows_*_stats.json), not from a
copied routing table -- MAIN and TO_HAND alone are ~2/3 of all decisions.

The reported metric is the operational one: exact-set top-k accuracy, i.e. did the
teacher's whole chosen SET come out as the top maxCount options. `top1` is that
metric restricted to single-pick decisions, so it is comparable to the transformer
line's held-out top-1 (0.624 for the 7-minute baseline, ~0.68 targeted).

Usage: uv run python train_gbdt.py [--rows grimm] [--rounds 400] [--holdout 0.1]
"""
from __future__ import annotations
import json, os, pickle, sys, time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
import feats  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


FAMILY = {
    "main": (-1,),
    "c7": (7,),
    "mid": (13, 15, 16, 21, 22, 40, 43),
    "low": (3, 5, 8),
}


def family_of(ctx):
    for name, ids in FAMILY.items():
        if ctx in ids:
            return name
    return "easy"


def load(tag):
    path = os.path.join(HERE, "results", f"rows_{tag}.pkl")
    per = defaultdict(lambda: ([], [], [], []))   # fam -> (ctx, qid, y, X)
    with open(path, "rb") as f:
        while True:
            try:
                ctx, qid, y, X = pickle.load(f)
            except EOFError:
                break
            fams = np.array([family_of(int(c)) for c in ctx])
            for fam in set(fams):
                m = fams == fam
                a, b, c2, d = per[fam]
                a.append(ctx[m]); b.append(qid[m]); c2.append(y[m]); d.append(X[m])
    out = {}
    for fam, (a, b, c2, d) in per.items():
        out[fam] = (np.concatenate(a), np.concatenate(b),
                    np.concatenate(c2), np.concatenate(d))
    return out


def groups_from_qid(qid):
    """LightGBM wants group SIZES in order; qid is already contiguous per query."""
    _, counts = np.unique(qid, return_counts=True)
    order = np.argsort(np.unique(qid))
    return counts[order]


def topk_accuracy(scores, y, qid):
    """Exact-set: the teacher's k picks are exactly the top-k scored options."""
    ok = tot = 0
    ok1 = tot1 = 0
    start = 0
    uq, counts = np.unique(qid, return_counts=True)
    for c in counts:
        s, yy = scores[start:start + c], y[start:start + c]
        k = int(yy.sum())
        start += c
        if k <= 0:
            continue
        pred = set(np.argsort(-s, kind="stable")[:k].tolist())
        truth = set(np.nonzero(yy)[0].tolist())
        tot += 1
        ok += pred == truth
        if k == 1:
            tot1 += 1
            ok1 += pred == truth
    return (ok / max(1, tot), tot, ok1 / max(1, tot1), tot1)


def main():
    tag = arg("--rows", "grimm")
    rounds = int(arg("--rounds", "400"))
    hold = float(arg("--holdout", "0.1"))
    lr = float(arg("--lr", "0.08"))
    leaves = int(arg("--leaves", "63"))
    data = load(tag)
    cat_idx = [feats.IDX[n] for n in feats.CATEGORICAL]
    models, report = {}, {}
    for fam in ("main", "c7", "mid", "low", "easy"):
        if fam not in data:
            continue
        ctx, qid, y, X = data[fam]
        uq = np.unique(qid)
        cut = uq[int(len(uq) * (1 - hold))]
        tr, va = qid < cut, qid >= cut
        if va.sum() == 0 or tr.sum() == 0:
            continue
        dtr = lgb.Dataset(X[tr], label=y[tr], group=groups_from_qid(qid[tr]),
                          categorical_feature=cat_idx, free_raw_data=False)
        dva = lgb.Dataset(X[va], label=y[va], group=groups_from_qid(qid[va]),
                          categorical_feature=cat_idx, reference=dtr,
                          free_raw_data=False)
        params = {"objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [1],
                  "learning_rate": lr, "num_leaves": leaves, "min_data_in_leaf": 40,
                  "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
                  "lambdarank_truncation_level": 12, "verbosity": -1, "seed": 42,
                  "num_threads": 0}
        t0 = time.time()
        bst = lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(40, verbose=False)])
        sc = bst.predict(X[va], num_iteration=bst.best_iteration)
        acc, n, acc1, n1 = topk_accuracy(sc, y[va], qid[va])
        models[fam] = bst
        report[fam] = {"queries_train": int(len(np.unique(qid[tr]))),
                       "queries_val": n, "topk": round(acc, 4),
                       "top1": round(acc1, 4), "n_top1": n1,
                       "trees": bst.best_iteration, "sec": round(time.time() - t0)}
        print(f"  {fam:<5} train_q {report[fam]['queries_train']:>7}  val_q {n:>6}  "
              f"topk {acc:.4f}  top1 {acc1:.4f} (n={n1})  trees {bst.best_iteration} "
              f"({report[fam]['sec']}s)", flush=True)

    outdir = os.path.join(HERE, "results", f"gbdt_{tag}")
    os.makedirs(outdir, exist_ok=True)
    for fam, bst in models.items():
        bst.save_model(os.path.join(outdir, f"{fam}.txt"))
    json.dump({"tag": tag, "rounds": rounds, "lr": lr, "leaves": leaves,
               "n_features": feats.N_FEATURES, "report": report},
              open(os.path.join(outdir, "report.json"), "w"), indent=1)
    tw = sum(r["queries_val"] * r["topk"] for r in report.values())
    tq = sum(r["queries_val"] for r in report.values())
    print(f"\n  overall exact-set top-k {tw/max(1,tq):.4f} over {tq} val decisions")
    print(f"  saved -> {outdir}")


if __name__ == "__main__":
    main()
