"""Where does the ranker disagree with the teacher, and on WHAT kind of option?

The workflow this enables is the one DeNA describes for Pokemon TCG Pocket
(invenglobal 24133): they found a specific misplay -- using "Speed Up" without
retreating -- and fixed it not by penalising the card, which made the AI avoid a
whole class of self-damage cards, but by adding one auxiliary feature that told
the model whether the retreat cost had actually been reduced. Correct usage rose
to 96.2%.

That loop needs an error report specific enough to name a feature. Held-out top-k
accuracy per family (train_gbdt.py) says how often we are wrong; this says what we
were wrong ABOUT:

  by context      which SelectContext costs the most absolute errors
  by opt_type     the OptionType we wrongly promoted, and the one we wrongly
                  dropped -- a promoted PLAY the teacher never makes is a
                  different bug from a missed ATTACH
  by card         the source/target card id on the mistakenly promoted option

Read the "promoted" table first: a card that keeps floating to the top when the
teacher does not want it is exactly the Speed Up case, and the fix is a feature
naming the precondition the model cannot currently see.

Usage: uv run python diag_errors.py [--tag grimm] [--top 18]
"""
from __future__ import annotations
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import lightgbm as lgb  # noqa: E402
import feats  # noqa: E402
from train_gbdt import load_family, FAMILY  # noqa: E402
from cg.api import SelectContext, OptionType, all_card_data  # noqa: E402

CTX_NAME = {int(m.value): m.name for m in SelectContext}
OPT_NAME = {int(m.value): m.name for m in OptionType}
NAME = {int(c.cardId): c.name for c in all_card_data()}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    tag = arg("--tag", "grimm")
    top = int(arg("--top", "18"))
    n_feat = int(arg("--n-feat", "0")) or None
    I = feats.IDX
    per_ctx = Counter(); per_ctx_err = Counter()
    promoted = Counter(); dropped = Counter()
    promoted_card = Counter(); dropped_card = Counter()
    n_dec = n_err = 0

    rows_tag = arg("--rows", None) or tag
    for fam in list(FAMILY) + ["easy"]:
        p = os.path.join(HERE, "results", f"gbdt_{tag}", f"{fam}.txt")
        if not os.path.exists(p):
            continue
        # one family at a time: the v6 corpus is 9.4GB and does not fit whole
        loaded = load_family(rows_tag, fam, n_feat)
        if loaded is None:
            continue
        ctx, qid, y, X, _opp = loaded
        bst = lgb.Booster(model_file=p)
        uq = np.unique(qid)
        cut = uq[int(len(uq) * 0.9)]
        m = qid >= cut
        if m.sum() == 0:
            continue
        sc = bst.predict(X[m])
        Xs, ys, qs, cs = X[m], y[m], qid[m], ctx[m]
        start = 0
        _, counts = np.unique(qs, return_counts=True)
        for c in counts:
            sl = slice(start, start + c)
            s, yy, rows = sc[sl], ys[sl], Xs[sl]
            cx = int(cs[start]); start += c
            k = int(yy.sum())
            if k <= 0:
                continue
            n_dec += 1; per_ctx[cx] += 1
            pred = set(np.argsort(-s, kind="stable")[:k].tolist())
            truth = set(np.nonzero(yy)[0].tolist())
            if pred == truth:
                continue
            n_err += 1; per_ctx_err[cx] += 1
            for i in pred - truth:          # wrongly promoted
                promoted[int(rows[i][I["opt_type"]])] += 1
                promoted_card[(int(rows[i][I["src_id"]]),
                               int(rows[i][I["tgt_id"]]))] += 1
            for i in truth - pred:          # wrongly dropped
                dropped[int(rows[i][I["opt_type"]])] += 1
                dropped_card[(int(rows[i][I["src_id"]]),
                              int(rows[i][I["tgt_id"]]))] += 1

    print(f"held-out decisions {n_dec}, wrong {n_err} ({n_err/max(1,n_dec):.3f})\n")
    print(f"{'context':<26}{'n':>7}{'err':>7}{'rate':>8}{'share_of_err':>14}")
    for cx, n in per_ctx.most_common(top):
        e = per_ctx_err[cx]
        print(f"{CTX_NAME.get(cx, cx):<26}{n:>7}{e:>7}{e/max(1,n):>8.3f}"
              f"{e/max(1,n_err):>14.3f}")

    print(f"\n{'wrongly PROMOTED option type':<34}{'n':>7}   "
          f"{'wrongly DROPPED option type':<30}{'n':>7}")
    a = promoted.most_common(10); b = dropped.most_common(10)
    for i in range(max(len(a), len(b))):
        la = f"{OPT_NAME.get(a[i][0], a[i][0]):<34}{a[i][1]:>7}" if i < len(a) else " " * 41
        lb = f"{OPT_NAME.get(b[i][0], b[i][0]):<30}{b[i][1]:>7}" if i < len(b) else ""
        print(f"{la}   {lb}")

    def show(title, c):
        print(f"\n{title}")
        for (s, t), n in c.most_common(12):
            print(f"  {n:>5}  src={NAME.get(s, s or '-')[:28]:<30} tgt={NAME.get(t, t or '-')[:28]}")
    show("wrongly PROMOTED (src -> tgt card)", promoted_card)
    show("wrongly DROPPED  (src -> tgt card)", dropped_card)

    json.dump({"decisions": n_dec, "errors": n_err,
               "per_ctx": {CTX_NAME.get(k, str(k)): [v, per_ctx_err[k]] for k, v in per_ctx.items()},
               "promoted_type": {OPT_NAME.get(k, str(k)): v for k, v in promoted.items()},
               "dropped_type": {OPT_NAME.get(k, str(k)): v for k, v in dropped.items()}},
              open(os.path.join(HERE, "results", f"diag_errors_{tag}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
