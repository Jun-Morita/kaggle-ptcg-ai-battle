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
import gc, json, os, pickle, sys, time
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


def _chunks(path):
    """Yield (ctx, qid, y, X, score, opp) chunks.

    Corpora grew columns over time: 4-tuples predate the teacher score and
    5-tuples predate the opponent archetype. Both are padded with zeros so an
    old corpus stays readable -- it simply never passes --min-score or --opp-mix.
    """
    with open(path, "rb") as f:
        while True:
            try:
                c = pickle.load(f)
            except EOFError:
                return
            n = len(c[0])
            if len(c) == 6:
                yield c
            elif len(c) == 5:
                yield c + (np.zeros(n, np.int8),)
            else:
                yield (c[0], c[1], c[2], c[3], np.zeros(n, np.float32),
                       np.zeros(n, np.int8))


# The field on 08-12, as a target for --opp-mix. Our corpus is dominated by
# late-July games (63% of the ladder was on our own deck then); these are the
# opponents the ladder actually finishes against.
FIELD_0812 = {1: .141, 2: .114, 3: .158, 4: .258, 5: .206, 6: .053, 7: .066}


def load_family(tag, fam, n_feat=None, min_score=None):
    """Read ONE family out of the row file, preallocated.

    The v6 corpus is 9.4GB on a 19GB box. Reading every family into lists and
    concatenating at the end peaks at roughly twice the file size and gets the
    process killed, so this makes two passes -- count, then fill -- and holds only
    the requested family. Two passes over a 9.4GB file cost about a minute of
    disk; an OOM costs the whole run.
    """
    path = os.path.join(HERE, "results", f"rows_{tag}.pkl")

    def keep(ctx, sc):
        m = np.array([family_of(int(c)) == fam for c in ctx])
        if min_score is not None:
            m &= (sc >= min_score)
        return m

    n_rows = 0
    n_cols = None
    for ctx, qid, y, X, sc, opp in _chunks(path):
        n_rows += int(keep(ctx, sc).sum())
        n_cols = X.shape[1]
    if n_rows == 0:
        return None
    cols = n_cols if n_feat is None else min(n_feat, n_cols)
    CTX = np.empty(n_rows, np.int16)
    QID = np.empty(n_rows, np.int32)
    Y = np.empty(n_rows, np.int8)
    X_ = np.empty((n_rows, cols), np.float32)
    OPP = np.empty(n_rows, np.int8)
    i = 0
    for ctx, qid, y, X, sc, opp in _chunks(path):
        m = keep(ctx, sc)
        k = int(m.sum())
        if not k:
            continue
        CTX[i:i + k] = ctx[m]; QID[i:i + k] = qid[m]; Y[i:i + k] = y[m]
        X_[i:i + k] = X[m][:, :cols]; OPP[i:i + k] = opp[m]
        i += k
    return CTX, QID, Y, X_, OPP


def opp_weights(opp, target):
    """Row weights that bend the OPPONENT mix of the corpus toward `target`.

    Not a filter: every decision is kept, and a game against a deck the ladder
    now barely plays simply counts for less. Opponents outside the table (code 0
    and anything unlisted) keep weight 1.0 rather than vanishing.
    """
    w = np.ones(len(opp), np.float32)
    seen = {int(k): int(v) for k, v in zip(*np.unique(opp, return_counts=True))}
    tot = sum(seen.get(k, 0) for k in target)
    if not tot:
        return w
    for code, share in target.items():
        n = seen.get(code, 0)
        if n:
            w[opp == code] = share / (n / tot)
    return w / w.mean()


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
    otag = arg("--out-tag", None) or tag
    # sweep_main.py on the v4 rows: main's top-k rose 0.6962 -> 0.7143 going from
    # 63 to 511 leaves and then flattened (1023: 0.7128, 2047: 0.7152, both inside
    # noise). 63 was simply too small for 284k training queries. 2047 triples the
    # node count for nothing, so 511 is the operating point.
    # Per-family values are allowed: "--leaves 511" sets everybody, while
    # "--leaves main=511,easy=31" overrides individual families. Until now all
    # five families shared one setting that was tuned on `main` alone, and the
    # small ones stop almost immediately under it (easy 14 trees, low 27) --
    # either they are genuinely easy, or 511 leaves overfits them in a handful of
    # rounds. A per-family sweep is the only way to tell the two apart.
    def per_fam(flag, default, cast):
        raw = arg(flag, None)
        if raw is None:
            return lambda _f: cast(default)
        if "=" not in raw:
            return lambda _f: cast(raw)
        tbl = dict(kv.split("=") for kv in raw.split(","))
        return lambda f: cast(tbl.get(f, default))

    lr_of = per_fam("--lr", "0.04", float)
    leaves_of = per_fam("--leaves", "511", int)
    minleaf_of = per_fam("--min-leaf", "100", int)
    seed = int(arg("--seed", "42"))
    # --n-feat truncates the row to its first N columns. The v6 features were
    # appended, so the first 318 columns ARE the v4b row: passing 318 trains the
    # same model on a bigger corpus and isolates corpus size from the features.
    n_feat = int(arg("--n-feat", "0")) or None
    fams = arg("--fam", "main,c7,mid,low,easy").split(",")
    # Keep only decisions made by teachers at or above this ladder score. The
    # score rides in the corpus, so a threshold costs a training run, not a
    # re-featurisation. Note the trade: teachers are already all >=1000, and
    # cutting at 1100 keeps 25.7% of seats -- the v6 result says corpus size is
    # worth real winrate, so quality has to beat a 4x data loss to be right.
    min_score = float(arg("--min-score", "0")) or None
    # Match the training distribution to the field, rather than adding to it.
    opp_mix = "--opp-mix" in sys.argv
    cat_idx = [feats.IDX[n] for n in feats.CATEGORICAL
               if n_feat is None or feats.IDX[n] < n_feat]
    models, report = {}, {}
    for fam in fams:
        loaded = load_family(tag, fam, n_feat, min_score)
        if loaded is None:
            continue
        ctx, qid, y, X, opp = loaded
        # qid is non-decreasing (rows are written in decision order), so the
        # holdout is a suffix and the split can be a SLICE. Boolean masks copied
        # the whole family a second time, which is 4GB+ for `main` on the v6
        # corpus and does not fit alongside the LightGBM Dataset.
        uq = np.unique(qid)
        cut = uq[int(len(uq) * (1 - hold))]
        i0 = int(np.searchsorted(qid, cut))
        if i0 == 0 or i0 >= len(qid):
            continue
        Xtr, Xva = X[:i0], X[i0:]
        ytr, yva, qtr, qva = y[:i0], y[i0:], qid[:i0], qid[i0:]
        wtr = opp_weights(opp[:i0], FIELD_0812) if opp_mix else None
        dtr = lgb.Dataset(Xtr, label=ytr, group=groups_from_qid(qtr), weight=wtr,
                          categorical_feature=cat_idx, free_raw_data=False)
        dva = lgb.Dataset(Xva, label=yva, group=groups_from_qid(qva),
                          categorical_feature=cat_idx, reference=dtr,
                          free_raw_data=False)
        params = {"objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [1],
                  "learning_rate": lr_of(fam), "num_leaves": leaves_of(fam),
                  "min_data_in_leaf": minleaf_of(fam),
                  "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
                  "lambdarank_truncation_level": 12, "verbosity": -1, "seed": seed,
                  "bagging_seed": seed + 1, "feature_fraction_seed": seed + 2,
                  "num_threads": 0}
        t0 = time.time()
        bst = lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(40, verbose=False)])
        sc = bst.predict(Xva, num_iteration=bst.best_iteration)
        acc, n, acc1, n1 = topk_accuracy(sc, yva, qva)
        models[fam] = bst
        report[fam] = {"leaves": leaves_of(fam), "lr": lr_of(fam),
                       "min_leaf": minleaf_of(fam),
                       "queries_train": int(len(np.unique(qtr))),
                       "queries_val": n, "topk": round(acc, 4),
                       "top1": round(acc1, 4), "n_top1": n1,
                       "trees": bst.best_iteration, "sec": round(time.time() - t0)}
        print(f"  {fam:<5} train_q {report[fam]['queries_train']:>7}  val_q {n:>6}  "
              f"topk {acc:.4f}  top1 {acc1:.4f} (n={n1})  trees {bst.best_iteration} "
              f"({report[fam]['sec']}s)", flush=True)
        del ctx, qid, y, X, opp, Xtr, Xva, ytr, yva, qtr, qva, dtr, dva, sc, loaded
        gc.collect()

    outdir = os.path.join(HERE, "results", f"gbdt_{otag}")
    os.makedirs(outdir, exist_ok=True)
    for fam, bst in models.items():
        bst.save_model(os.path.join(outdir, f"{fam}.txt"))
    json.dump({"tag": tag, "rounds": rounds, "min_score": min_score,
               "opp_mix": opp_mix, "seed": seed,
               "n_features": n_feat or feats.N_FEATURES, "report": report},
              open(os.path.join(outdir, "report.json"), "w"), indent=1)
    tw = sum(r["queries_val"] * r["topk"] for r in report.values())
    tq = sum(r["queries_val"] for r in report.values())
    print(f"\n  overall exact-set top-k {tw/max(1,tq):.4f} over {tq} val decisions")
    print(f"  saved -> {outdir}")


if __name__ == "__main__":
    main()
