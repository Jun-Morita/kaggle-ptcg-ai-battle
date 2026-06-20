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

## Phase 3: ミラー特化 RL（再設計, rl_phase3_mirror.py）
2026-06-20 メタ解析(exp011)で field が Lucario-ex 57% に回転し、**v003 がミラーに負けている(0.31)**
と判明 → RL の的を「Lucario で Crustle を倒す(sparse・困難)」から **「Lucario ミラーを勝つ」** へ再設定。

**なぜミラーが理想的 RL 課題か**:
- 勝てる（対称＝技量勝負, sparse な Hariyama 切替不要）
- 価値最大（field の過半 57%）
- **belief が完全**（相手デッキ=自デッキ=LUCARIO と既知）→ exp008「belief で探索が活きる」の最良ケース
- v003 最大の弱点（ミラー負け）を直接埋める

**Phase 2 崩壊への対策**:
1. 相手 = 固定の stock lucario_v2（field プロキシ）→ moving target を排し value ラベルを接地
2. 経験リプレイ（直近 K 世代をまとめて学習）
3. checkpoint gating / 崩壊復帰（best eval を保持、margin 超の退行は best へ巻き戻し）

**成功基準**: net(belief-MCTS) が stock lucario_v2 にミラーで **>0.55**（v003 ref ~0.47）。
達成なら v003 を超えるミラー操縦＝提出候補。設定: gen12 / search24 / games28 / eval16 / replay3。
出力: `results/rl3_best.pth`（最良）, `rl3_latest.pth`, `rl_phase3_history.json`。

**Phase 3 結果（正直なネガティブ, gating で崩壊は防止）**:
- ミラー eval(vs stock): gen1 で 0.312 が最良、以降伸びず（0.0-0.31 で振動）。self-play は常時負け越し(~5-8/28)。
- 内訳: BC greedy 0.17 → BC+belief-MCTS(search24) 0.31。**伸ばしたのは探索であって RL 学習ではない**。
- **探索量スケーリング eval（決定的）**: search 24→48→96 で 0.312→0.188→**0.125** と**悪化**（0.05-0.18s/手）。
  良い value なら探索は効くはず → **value ネットが不良**で深い探索が誤推定を増幅。
- **結論**: 3本の証拠（Phase2 崩壊 / Phase3 0.31 天井 / 探索増で悪化）で、warm-start belief-MCTS は
  強い rule-based(stock lucario_v2) をミラーで超えない。ボトルネック＝value 品質（速度・探索量でない）。
- 原理的次手（未実施, 後半の計算資源向け）: **stock vs stock の大量対戦で value を較正**してから MCTS に載せる。
  現状は ROI が悪く打ち切り。ラダー主力は rule-based(v004 Crustle / v003)。

## 結論 / 次
- Phase 1 net (`results/bc_v003_multi.pth`) = warm-start。Phase 2 best = `rl_best_gen1.pth`（負け確定）。
- Phase 3 = ミラー特化で再挑戦（背景実行中, ID b4erl9yws）。
- 現実解: ラダー主力は依然 **rule-based(v003 / v004 Crustle カウンター)**。RL は >0.55 を出せれば
  初めて提出候補。レポートには Phase 2 の誠実なネガティブ＋Phase 3 の再設計を記載。
