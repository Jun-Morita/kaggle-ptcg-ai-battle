"""LightGBM models -> a compact pure-Python scorer the submission can carry.

The submission sandbox has no numpy (v015 died on that) and a total 600s budget
per game, so whatever ships has to be stdlib-only and fast per decision. A tree
ensemble is a good fit: inference is pointer-chasing over small tuples, no matrix
math, and the whole model is a few hundred KB against the transformer's 53.6MB.

Each tree is flattened into a parallel-array node table:
    left[i], right[i]   child node indices (negative = leaf id, ~leaf)
    feat[i]             feature index, or -1 for a leaf
    thr[i]              numeric threshold, or None for a categorical split
    cats[i]             frozen set of category codes taking the LEFT branch
    val[i]              leaf value
LightGBM's default_left decides where a missing/NaN value goes; our features are
always concrete floats, but the flag is kept so a future sparse feature does not
silently take the wrong branch.

Written as a plain pickle of tuples, so the loader in gbdt_policy.py is three
lines and needs nothing but the stdlib.

Usage: uv run python export_pure.py [--tag grimm] [--out gbdt_pure.pkl]
"""
from __future__ import annotations
import json, os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lightgbm as lgb  # noqa: E402
import feats  # noqa: E402

FAMS = ("main", "c7", "mid", "low", "easy")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def flatten(tree):
    """Depth-first flatten of one dump_model tree into parallel arrays.

    Missing-value routing (default_left) is deliberately NOT carried: base_state
    and option_rows fill every slot with a concrete float, so no NaN can reach a
    split. parity_pure.py checks that assumption against LightGBM on real rows
    rather than trusting it.
    """
    left, right, feat, thr, cats, val = [], [], [], [], [], []

    def walk(node):
        if "leaf_value" in node:
            i = len(left)
            left.append(0); right.append(0); feat.append(-1)
            thr.append(0.0); cats.append(None); val.append(float(node["leaf_value"]))
            return i
        i = len(left)
        left.append(0); right.append(0)
        feat.append(int(node["split_feature"]))
        if node.get("decision_type") == "==":
            # categorical: threshold is "a||b||c"; those categories go LEFT
            thr.append(None)
            cats.append(frozenset(int(float(x)) for x in str(node["threshold"]).split("||")))
        else:
            thr.append(float(node["threshold"]))
            cats.append(None)
        val.append(0.0)
        left[i] = walk(node["left_child"])
        right[i] = walk(node["right_child"])
        return i

    walk(tree["tree_structure"])
    return (left, right, feat, thr, cats, val)


def main():
    tag = arg("--tag", "grimm")
    out = arg("--out", os.path.join(HERE, "results", f"gbdt_pure_{tag}.pkl"))
    src = os.path.join(HERE, "results", f"gbdt_{tag}")
    models, stats = {}, {}
    for fam in FAMS:
        p = os.path.join(src, f"{fam}.txt")
        if not os.path.exists(p):
            continue
        bst = lgb.Booster(model_file=p)
        dumped = bst.dump_model()
        trees = [flatten(t) for t in dumped["tree_info"]]
        models[fam] = trees
        stats[fam] = {"trees": len(trees), "nodes": sum(len(t[0]) for t in trees)}
        print(f"  {fam:<5} trees {stats[fam]['trees']:>4}  nodes {stats[fam]['nodes']:>7}")

    blob = {"features": feats.FEATURES, "family": {
        "main": [-1], "c7": [7], "mid": [13, 15, 16, 21, 22, 40, 43],
        "low": [3, 5, 8]}, "models": models}
    with open(out, "wb") as f:
        pickle.dump(blob, f, protocol=4)
    print(f"\n  wrote {out} ({os.path.getsize(out)/1e6:.2f}MB)")
    json.dump(stats, open(os.path.join(src, "pure_stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
