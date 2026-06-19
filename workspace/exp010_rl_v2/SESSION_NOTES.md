# exp010_rl_v2 — SESSION NOTES

設計は `PLAN.md`（3段階: 多相手BC → belief-MCTS RL微調整 → 評価/提出）。

## Phase 1: 多相手 BC（warm-start）
- 教師 = v003 anti-Crustle(最良, Lucario デッキ)。相手 = {Crustle control, lucario_v2, dragapult, iono}＋ミラー。
- `bc_phase1.py`（exp006 のモデル/特徴量＋exp007 の v003方策を流用）。600ゲーム/30エポック。
- 結果: 模倣精度 **0.792**、value_loss 0.083。
- **greedy 評価 (探索なし, n=24)**: crustle 0.375 / lucario_v2 0.167 / dragapult 0.125 / random 0.75 → 平均 **0.222**。
  - exp006 同様 **BC単体は教師に遠く未達**（誤差累積）。**想定通り＝warm-start 素材**（単体agentではない）。
  - 多相手にしても greedy 強度は単一教師(exp006 0.389)と同程度かやや下。BC の限界を再確認。

## Phase 2: belief-MCTS RL 微調整（warm-start ＋ メタ相手プール, search=16）
- 8世代 / 24games・eval8 / seed43。各世代 `rl_gen{N}.pth`＋`rl_latest.pth`。
- 結果（eval 勝率, n=8/相手）:

  | gen | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
  |---|---|---|---|---|---|---|---|---|
  | Crustle | .25 | **.375** | .25 | .125 | **.5** | .25 | .125 | .125 |
  | Lucario | .125 | **.375** | .25 | .25 | .125 | .125 | .25 | .0 |
  | loss | .65 | .67 | .69 | .67 | .62 | .52 | .31 | .24 |

- **結論＝正直なネガティブ**: loss は単調低下（self-play ラベルに適合）だが eval 勝率は上がらず、
  後半は **方策崩壊**（gen7 lucario 0.0, self-play 対 Crustle 0-16）。典型的な self-play 過適合。
- ピークは gen1（両 0.375, `rl_best_gen1.pth` に退避）。それでも v003（Crustle ~0.55＋プール圧勝）に未達。
- **8世代の belief-MCTS RL は rule-based v003 を超えなかった → 提出不可水準**。

## なぜ崩壊したか（仮説 / 次の改善余地）
1. self-play 対戦相手にネット自身が混ざらず固定ルール相手のみ → 多様性不足で TD ラベルが偏る。
2. 1世代の試合数(24)・search(16)が小さくサンプルが少→ノイズで方策が振れる。
3. value ラベル(TD)とMCTS方策ラベルの整合が弱く、loss低下＝崩壊を招いた可能性。
4. 改善案: (a) 経験リプレイで過去世代を混ぜる, (b) ベストモデルでの early-stop/選抜(PBT風),
   (c) search数↑＋games↑（GPU空き時間に長時間）, (d) 報酬を「Crustle特化」へ絞る。

## 結論 / 次
- Phase 1 net (`results/bc_v003_multi.pth`) = warm-start。Phase 2 best = `rl_best_gen1.pth`。
- 現実解: ラダーの主力は依然 **v003(LB~1123, rule-based)**。RL は後半の学習系競争に備えた長期投資で、
  現時点では未達。レポートには「素朴な RL は belief を入れても rule-based を超えない」を誠実に記載。
