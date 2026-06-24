"""Dictionary / k-NN behavior cloning — does RETRIEVING the expert's move beat
COMPRESSING it into an MLP (which capped at 0.49 action-match)?

Idea (user's): store tomatomato's decisions as a dictionary keyed by STATE; at a new
state, retrieve the nearest expert state(s), read the action-signature they chose, and
play the current option whose features best match that signature. No compression -> if
this beats the MLP's 0.49, the limiter was the model class; if it ties ~0.49, the limiter
is the FEATURES (representation) and richer learning won't help either.

Feature layout (from bc_dataset): row = [state(12) | option(16)].
Usage: uv run python knn_bc.py
"""
from __future__ import annotations
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SDIM = 12  # state_feats width (rest is option_feats)


def main():
    d = np.load(os.path.join(HERE, "results", "bc_data.npz"))
    X, groups, y = d["X"], d["groups"], d["y"]
    offs = np.concatenate([[0], np.cumsum(groups)])
    n_dec = len(groups)

    # per-decision: state vector, the option rows, the chosen option's option-features
    states = np.zeros((n_dec, SDIM), dtype=np.float32)
    chosen_sig = np.zeros((n_dec, X.shape[1] - SDIM), dtype=np.float32)
    opt_rows = []
    for i in range(n_dec):
        s, e = offs[i], offs[i + 1]
        states[i] = X[s, :SDIM]                       # state shared across the decision's options
        chosen_sig[i] = X[s + y[i], SDIM:]            # the option-features the expert picked
        opt_rows.append(X[s:e, SDIM:])                # all options' option-features

    rng = np.random.default_rng(0)
    perm = rng.permutation(n_dec)
    n_val = n_dec // 5
    val = perm[:n_val]
    tr = perm[n_val:]
    tr_states = states[tr]

    rand_acc = float(np.mean([1.0 / groups[i] for i in val]))

    for K in (1, 3, 5):
        match = 0
        cover = 0
        for i in val:
            # nearest expert states (by state distance)
            dists = np.sum((tr_states - states[i]) ** 2, axis=1)
            nn = tr[np.argsort(dists)[:K]]
            # average the chosen action-signatures of the K nearest expert states
            sig = chosen_sig[nn].mean(0)
            # pick the current option whose option-features are closest to that signature
            od = np.sum((opt_rows[i] - sig) ** 2, axis=1)
            pick = int(np.argmin(od))
            match += int(pick == y[i])
            cover += 1
        print(f"k={K}: action-match={match/cover:.3f}  (MLP=0.49, random={rand_acc:.3f})")

    # also: how close are val states to their nearest expert state? (coverage / distribution)
    nnd = []
    for i in val:
        dists = np.sum((tr_states - states[i]) ** 2, axis=1)
        nnd.append(float(np.sqrt(dists.min())))
    nnd = np.array(nnd)
    print(f"\nnearest-expert-state distance: median={np.median(nnd):.3f} p90={np.percentile(nnd,90):.3f} "
          f"(0 = identical state already in dictionary)")
    frac_close = float(np.mean(nnd < 0.30))
    print(f"fraction of val states with a CLOSE expert match (<0.30): {frac_close:.2f} "
          f"-> the rest would fall back to the simple policy")


if __name__ == "__main__":
    main()
