"""exp032 go/no-go — retest exp014's mid-game value learnability at ~100k games.

Protocol mirrors exp014: game-level holdout (no state leakage across the split),
phase = turn/game_len, MID-GAME = phase in [0.4, 0.6]. Models: prize_diff alone
(baseline), logistic regression, HistGradientBoosting (nonlinear capacity).
GO if mid-game AUC >= 0.70 and clearly above the prize_diff baseline.
"""
from __future__ import annotations
import glob, os, sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
FEATS = ["prize_diff", "prize_me", "prize_opp", "act_hp_me", "act_hp_opp",
         "act_ene_me", "act_ene_opp", "ene_board_me", "ene_board_opp",
         "bench_me", "bench_opp", "hand_me", "hand_opp", "deck_me",
         "turn", "going_first", "opp_status"]


def main():
    files = sorted(glob.glob(os.path.join(HERE, "data", "rows_w*.csv")))
    # deck_me appears twice (feature + deck name) -> pandas suffixes the later ones
    df = pd.concat([pd.read_csv(f, dtype={"game": str}) for f in files], ignore_index=True)
    df.columns = (["game", "pov", "turn_key"] + FEATS + ["label", "deckname_me", "deckname_opp", "game_len"])
    df = df[df.game_len > 0].copy()
    df["phase"] = df["turn_key"] / df["game_len"]
    games = df["game"].unique()
    rng = np.random.RandomState(0)
    rng.shuffle(games)
    ho = set(games[: len(games) // 5])
    te = df["game"].isin(ho)
    Xtr, ytr = df.loc[~te, FEATS].values, df.loc[~te, "label"].values
    Xte, yte = df.loc[te, FEATS].values, df.loc[te, "label"].values
    phase_te = df.loc[te, "phase"].values
    print(f"rows={len(df):,} games={len(games):,} | train={len(ytr):,} test={len(yte):,}")

    lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    gb = HistGradientBoostingClassifier(max_iter=300, random_state=0).fit(Xtr, ytr)
    p_lr = lr.predict_proba(Xte)[:, 1]
    p_gb = gb.predict_proba(Xte)[:, 1]
    p_base = df.loc[te, "prize_diff"].values  # monotone baseline

    def report(name, lo, hi):
        m = (phase_te >= lo) & (phase_te < hi)
        if m.sum() < 100 or len(set(yte[m])) < 2:
            return
        print(f"  phase {lo:.1f}-{hi:.1f} (n={m.sum():7,}): "
              f"prize_diff {roc_auc_score(yte[m], p_base[m]):.3f} | "
              f"LR {roc_auc_score(yte[m], p_lr[m]):.3f} | "
              f"GB {roc_auc_score(yte[m], p_gb[m]):.3f}")

    print("\n=== AUC by game phase (test games) ===")
    for lo in np.arange(0.0, 1.0, 0.2):
        report("", lo, lo + 0.2)
    m = (phase_te >= 0.4) & (phase_te < 0.6)
    mid_gb = roc_auc_score(yte[m], p_gb[m])
    mid_base = roc_auc_score(yte[m], p_base[m])
    print(f"\nMID-GAME (0.4-0.6): GB {mid_gb:.3f} vs prize_diff {mid_base:.3f} "
          f"(exp014 @319 games: 0.585-0.637)")
    print("VERDICT:", "GO (>=0.70, above baseline)" if (mid_gb >= 0.70 and mid_gb > mid_base + 0.02)
          else "NO-GO (mid-game variance is game-intrinsic)")


if __name__ == "__main__":
    main()
