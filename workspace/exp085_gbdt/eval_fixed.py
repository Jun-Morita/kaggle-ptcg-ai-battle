"""Score several models on ONE fixed held-out set.

train_gbdt.py reports top-k on its own validation split, and --min-score filters
the validation rows as well as the training rows. So the v7 threshold sweep
produced four numbers measured on four different problems: the 1100 model's
0.7677 is "how well it predicts >=1100 teachers", which is not comparable to the
control's 0.7836 over everybody. A harder held-out set can look like a worse
model, and a smaller one can look like a better one.

This evaluates every model on the SAME decisions -- by default the control's
held-out tail, i.e. the full teacher population -- so the only thing that differs
is what the model was trained on.

Usage: uv run python eval_fixed.py --rows v7 --tags v7,v7m1050,v7m1100,v7m1150
                                   [--eval-min-score 0] [--holdout 0.1]
"""
from __future__ import annotations
import os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
from train_gbdt import load_family, topk_accuracy, FAMILY  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    rows = arg("--rows", "v7")
    tags = arg("--tags", "v7").split(",")
    hold = float(arg("--holdout", "0.1"))
    # which decisions to be judged on. 0 = the whole teacher population, which is
    # the population the ladder actually makes us play against.
    ev_min = float(arg("--eval-min-score", "0")) or None
    fams = list(FAMILY) + ["easy"]
    res = defaultdict(dict)
    tot = defaultdict(lambda: [0.0, 0])
    for fam in fams:
        loaded = load_family(rows, fam, None, ev_min)
        if loaded is None:
            continue
        _ctx, qid, y, X, _opp = loaded
        # the SAME split rule as training, so no model is scored on rows it saw
        uq = np.unique(qid)
        cut = uq[int(len(uq) * (1 - hold))]
        i0 = int(np.searchsorted(qid, cut))
        Xv, yv, qv = X[i0:], y[i0:], qid[i0:]
        for t in tags:
            p = os.path.join(HERE, "results", f"gbdt_{t}", f"{fam}.txt")
            if not os.path.exists(p):
                continue
            sc = lgb.Booster(model_file=p).predict(Xv)
            acc, n, _a1, _n1 = topk_accuracy(sc, yv, qv)
            res[t][fam] = (acc, n)
            tot[t][0] += acc * n
            tot[t][1] += n
        del loaded, _ctx, qid, y, X, Xv, yv, qv

    hdr = f"{'family':<7}" + "".join(f"{t:>11}" for t in tags)
    print(f"\nheld-out = {rows}" + (f", teachers >= {ev_min}" if ev_min else
                                    ", ALL teachers") + f", last {hold:.0%}")
    print(hdr)
    for fam in fams:
        if not any(fam in res[t] for t in tags):
            continue
        n = next(res[t][fam][1] for t in tags if fam in res[t])
        print(f"{fam:<7}" + "".join(
            f"{res[t][fam][0]:>11.4f}" if fam in res[t] else f"{'-':>11}"
            for t in tags) + f"   n={n}")
    print(f"{'overall':<7}" + "".join(
        f"{tot[t][0]/max(1,tot[t][1]):>11.4f}" for t in tags)
        + f"   n={tot[tags[0]][1]}")


if __name__ == "__main__":
    main()
