# exp032 — エンジンソース活用: 大規模自己対戦で価値較正 go/no-go を再テスト

## 背景・仮説
RL 6連敗の核心 exp014「中盤の価値は学習不能（AUC 0.585-0.637）」は **319試合の極小データ**での
結論（rich 特徴は train 0.999＝データ量が限界の可能性）。エンジンソース公開（disc 717141）により
ネイティブビルド → 大規模データ生成が初めて可能に。**データ 300倍で中盤 AUC が上がるか**が go/no-go。
- 上がらない → 「中盤分散はゲーム内在」が決定的に確定（レポート強化）。
- 上がる（AUC ≥ 0.70 目安）→ belief-PIMC のロールアウト評価/価値ネット MCTS が解禁。

## ネイティブエンジン
`g++ -std=c++20 -O2 -fPIC -shared Export.cpp -o libcg.so`（15秒, 警告なし）→ `native/cg/` に配置、
公式 cg パッケージと完全互換（run_match 動作）。乱択 10,300 steps/s。

## データ生成（datagen.py, 実行中 2026-07-03）
- 4 ワーカー × 25,000 試合 = **10万試合**目標。デッキプール: v_trev/charmq/lucario/grimmsnarl(+dragapult)
  のランダムペア、操縦は revenge(RB=50) 汎用。
- 1行 = (game, pov, turn) + exp014 と同一の 17 scalars（value_calib.FEATS を import＝比較可能性確保）
  + label(そのpovが勝ったか) + デッキ名 + game_len。ターン毎 1 サンプル/側。
- 出力: `data/rows_w{0-3}.csv`（gitignored）。

## 次ステップ
1. 生成完了後: exp014 value_calib と同プロトコル（episode-level holdout, mid-game phase 0.4-0.6 AUC）
   で再評価。ベースライン = prize_diff 単独。
2. 並行トラック A: CardImpl.h から攻撃/効果テーブル抽出 → Stage 2 belief-PIMC の脅威モデル。

## 結果（2026-07-03）— **GO: exp014 の中核 negative が覆った**
- 生成: 99,328試合 / 2,481,160行（4ワーカー, 0.12s/game, native engine）。
- value_retest.py（game-level holdout 20%, exp014 同一 17 scalars）:
  | phase | prize_diff | LR | GB |
  |---|---|---|---|
  | 0.0-0.2 | 0.519 | 0.517 | 0.549 |
  | 0.2-0.4 | 0.604 | 0.627 | 0.694 |
  | **0.4-0.6** | **0.650** | 0.691 | **0.784** |
  | 0.6-0.8 | 0.797 | 0.814 | 0.886 |
  | 0.8-1.0 | 0.908 | 0.920 | 0.956 |
- **中盤 AUC 0.784（GB）**: exp014 の 0.585-0.637 → データ312倍で +0.15。ベースライン 0.650 を明確に超過。
  「中盤分散はゲーム内在」は**データ不足の誤診**だった（train 0.999/val 0.585 の overfit が示唆していた通り）。
- 注意（誠実性）: この価値は「我々の rule-based 方策の自己対戦分布」上のもの。ただし**探索のロールアウト
  方策は我々自身**なので、on-policy 価値はまさに探索が必要とするもの＝用途に整合。
- exp010 の教訓: 価値の質 ≠ エージェントの強さ。**次 = 対戦での実証**（Stage 2b）。

## 次ステップ（Stage 2b: value-guided guard/PIMC）
1. GB を純 numpy に蒸留（提出物は pure-python 制約; 小型 MLP or 木のフラット化）。
2. guard の doom 3値判定を value スコアに置換 or 併用（ロールアウト全実行→終端 value 平均で候補比較）。
3. n=200 field + paired で v013 比較 → 勝てば v014。
