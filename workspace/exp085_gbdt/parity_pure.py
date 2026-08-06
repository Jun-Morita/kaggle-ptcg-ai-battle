"""Does the shipped pure-Python scorer agree with LightGBM, decision for decision?

The transformer line shipped on a 500/500 argmax parity check between torch,
numpy and the pure port; the same discipline applies here, and matters more,
because the export re-implements categorical splits by hand ("does this feature's
value fall in the LEFT set") -- the one place a silent mismatch is plausible.

Two things are checked, and the second is the one that can actually cost a game:
  raw       max |pure_score - lgb_score| over sampled rows
  ranking   the top-k SET picked from pure scores equals the one from LightGBM

Usage: uv run python parity_pure.py [--tag grimm] [--n 400]
"""
from __future__ import annotations
import os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
from gbdt_policy import score_rows, load_pure  # noqa: E402
from train_gbdt import load, family_of  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    tag = arg("--tag", "grimm")
    # A model tag and a corpus tag are not the same thing: v4b is trained on the
    # v4 rows with bigger trees. Defaulting --rows to --tag made this exit with
    # FileNotFoundError, and because run_v4b.sh did not stop on it, an artifact
    # got built with NO parity check at all. Ship-path verification must not be
    # skippable by a missing file.
    rows = arg("--rows", None) or tag
    n = int(arg("--n", "400"))
    pure = load_pure(os.path.join(HERE, "results", f"gbdt_pure_{tag}.pkl"))
    data = load(rows)
    worst = 0.0
    same = tot = 0
    for fam, (_ctx, qid, y, X) in data.items():
        if fam not in pure["models"]:
            continue
        bst = lgb.Booster(model_file=os.path.join(HERE, "results", f"gbdt_{tag}", f"{fam}.txt"))
        uq = np.unique(qid)[-n:]
        for q in uq:
            m = qid == q
            rows = X[m].tolist()
            ref = bst.predict(X[m])
            got = score_rows(pure, fam, rows)
            worst = max(worst, float(np.max(np.abs(np.asarray(got) - ref))))
            k = max(1, int(y[m].sum()))
            a = set(np.argsort(-np.asarray(got), kind="stable")[:k].tolist())
            b = set(np.argsort(-ref, kind="stable")[:k].tolist())
            same += (a == b)
            tot += 1
    if tot == 0:
        raise SystemExit("PARITY FAILED -- no rows compared (wrong --rows tag?)")
    print(f"  max |pure - lgb| = {worst:.3e}")
    print(f"  identical top-k set: {same}/{tot}")
    if same != tot:
        raise SystemExit("PARITY FAILED -- do not ship")
    print("  PARITY OK")


if __name__ == "__main__":
    main()
