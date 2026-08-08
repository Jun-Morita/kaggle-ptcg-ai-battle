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
from train_gbdt import _chunks, family_of  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def tail_family(tag, fam, n_q, n_feat=None):
    """The last n_q queries of one family, without loading the corpus.

    Parity only needs a sample, and the v6 rows are 9.4GB. This keeps a rolling
    buffer of recent rows for the family and returns the tail, so the check costs
    one streaming read instead of the training loader's full materialisation.
    """
    path = os.path.join(HERE, "results", f"rows_{tag}.pkl")
    keep_q, keep_y, keep_X = [], [], []
    for ctx, qid, y, X, _sc in _chunks(path):
        m = np.array([family_of(int(c)) == fam for c in ctx])
        if not m.any():
            continue
        keep_q.append(qid[m]); keep_y.append(y[m]); keep_X.append(X[m])
        while sum(len(a) for a in keep_q) > 400000 and len(keep_q) > 1:
            keep_q.pop(0); keep_y.pop(0); keep_X.pop(0)
    if not keep_q:
        return None
    q = np.concatenate(keep_q); yy = np.concatenate(keep_y)
    XX = np.vstack(keep_X)
    if n_feat:
        XX = XX[:, :n_feat]
    uq = np.unique(q)[-n_q:]
    m = np.isin(q, uq)
    return q[m], yy[m], XX[m]


def main():
    tag = arg("--tag", "grimm")
    # A model tag and a corpus tag are not the same thing: v4b is trained on the
    # v4 rows with bigger trees. Defaulting --rows to --tag made this exit with
    # FileNotFoundError, and because run_v4b.sh did not stop on it, an artifact
    # got built with NO parity check at all. Ship-path verification must not be
    # skippable by a missing file.
    rows = arg("--rows", None) or tag
    n = int(arg("--n", "400"))
    n_feat = int(arg("--n-feat", "0")) or None
    # An ensemble export has no single booster to compare against, so the
    # reference is the MEAN of the boosters it was merged from -- which is exactly
    # what the 1/K leaf scaling in export_pure.py is supposed to reproduce.
    tags = [t for t in (arg("--tags", "") or "").split(",") if t] or [tag]
    pure = load_pure(os.path.join(HERE, "results", f"gbdt_pure_{tag}.pkl"))
    worst = 0.0
    same = tot = 0
    for fam in pure["models"]:
        got_data = tail_family(rows, fam, n, n_feat)
        if got_data is None:
            continue
        qid, y, X = got_data
        bsts = [lgb.Booster(model_file=os.path.join(HERE, "results", f"gbdt_{t}", f"{fam}.txt"))
                for t in tags]
        for q in np.unique(qid):
            m = qid == q
            rows_l = X[m].tolist()
            ref = sum(b.predict(X[m]) for b in bsts) / len(bsts)
            got = score_rows(pure, fam, rows_l)
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
