"""exp032 Stage 2b(1) — train a small MLP on the 2.48M rows and export pure-numpy
weights (submission has no sklearn). Report mid-game AUC vs the GB reference (0.784).

Output: value_mlp.npz  (W0,b0,W1,b1,W2,b2, mean, std)  -> predict = sigmoid(mlp(zscore(x)))
"""
from __future__ import annotations
import glob, os
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
FEATS = ["prize_diff", "prize_me", "prize_opp", "act_hp_me", "act_hp_opp",
         "act_ene_me", "act_ene_opp", "ene_board_me", "ene_board_opp",
         "bench_me", "bench_opp", "hand_me", "hand_opp", "deck_me",
         "turn", "going_first", "opp_status"]


def main():
    files = sorted(glob.glob(os.path.join(HERE, "data", "rows_w*.csv")) + glob.glob(os.path.join(HERE, "data2", "rows_w*.csv")))
    parts = []
    for f in files:
        d = pd.read_csv(f, dtype={"game": str})
        d["game"] = os.path.basename(os.path.dirname(f)) + "/" + d["game"]  # avoid id collisions across dirs
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df.columns = (["game", "pov", "turn_key"] + FEATS + ["label", "deckname_me", "deckname_opp", "game_len"])
    df = df[df.game_len > 0].copy()
    df["phase"] = df["turn_key"] / df["game_len"]
    games = df["game"].unique()
    rng = np.random.RandomState(0)
    rng.shuffle(games)
    ho = set(games[: len(games) // 5])
    te = df["game"].isin(ho)

    X = df[FEATS].values.astype(np.float64)
    mean, std = X[~te].mean(0), X[~te].std(0) + 1e-9
    Z = (X - mean) / std
    y = df["label"].values

    mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu", alpha=1e-4,
                        batch_size=4096, learning_rate_init=1e-3, max_iter=30,
                        early_stopping=True, n_iter_no_change=3, random_state=0, verbose=False)
    mlp.fit(Z[~te.values], y[~te.values])
    p = mlp.predict_proba(Z[te.values])[:, 1]
    yte, phase_te = y[te.values], df.loc[te, "phase"].values
    for lo in (0.2, 0.4, 0.6):
        m = (phase_te >= lo) & (phase_te < lo + 0.2)
        print(f"phase {lo:.1f}-{lo+0.2:.1f}: MLP AUC {roc_auc_score(yte[m], p[m]):.3f}")
    m = (phase_te >= 0.4) & (phase_te < 0.6)
    print(f"MID-GAME MLP: {roc_auc_score(yte[m], p[m]):.3f} (GB ref 0.784, base 0.650)")

    W0, W1, W2 = mlp.coefs_
    b0, b1, b2 = mlp.intercepts_
    out = os.path.join(HERE, os.environ.get("MLP_OUT", "value_mlp.npz"))
    np.savez(out, W0=W0, b0=b0, W1=W1, b1=b1, W2=W2, b2=b2, mean=mean, std=std)
    # parity check: manual forward pass vs sklearn
    def fwd(Zb):
        h = np.maximum(Zb @ W0 + b0, 0)
        h = np.maximum(h @ W1 + b1, 0)
        return 1 / (1 + np.exp(-(h @ W2 + b2))).ravel()
    d = np.abs(fwd(Z[te.values][:1000]) - p[:1000]).max()
    print(f"saved {out}; numpy-forward parity max|diff| = {d:.2e}")


if __name__ == "__main__":
    main()
