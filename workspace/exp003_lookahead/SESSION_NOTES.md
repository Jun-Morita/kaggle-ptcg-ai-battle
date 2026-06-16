# exp003_lookahead — SESSION NOTES

## 仮説
Search API（`search_begin/step/end`）で各選択肢を先読み評価し argmax する自前 agent が、
exp002 のルールベースのバー（プール平均 lucario_v2 = 0.680）を超えられるか。

## やったこと
- `spike_search.py`: Search API を実機検証。中盤 MAIN 局面で各選択肢を `search_step` し、
  状態デルタ（opp HP, サイド, KO, result）を読めることを確認。**API は完全に機能**。
  - 注意: `searchId` は `SearchState` 側（`observation` には無い）。
  - `search_begin` には隠し情報を counts 一致で渡す（公式 MCTS サンプル流: 相手を Snorlax 1072 / 基本エネ 1 で穴埋め）。
- `agent_lookahead.py`: 自己完結の先読み agent。2モード:
  - `one_ply`: 各選択肢を1ステップ進めた直後の状態を V() 評価。
  - `turn_rollout`: 選択肢を選んだ後、自ターンをグリーディ継続し終了時状態を V() 評価。
  - V() = サイド差*1000 + 盤面HP差*0.1 + 相手アクティブHP圧*0.2 + 駒数*5 + アクティブ存在。
  - 探索失敗時は安全なデフォルト選択にフォールバック（クラッシュしない）。
- `eval_lookahead.py`: random / dragapult / lucario_v1 / lucario_v2 と対戦し集計（`results/lookahead_eval.json`）。

## 結果 (2026-06-17, deck=lucario_v2, n=30/相手, swap, seed=42) — **NEGATIVE**

| モード | vs random | vs dragapult | vs lucario_v1 | vs lucario_v2 | 対ルールベース平均 |
|---|---|---|---|---|---|
| one_ply | 0.867 | 0.133 | 0.467 | 0.033 | **0.211** |
| turn_rollout | 0.800 | 0.167 | 0.500 | 0.133 | **0.267** |

- バー 0.680 に遠く及ばず。**ナイーブな探索 agent は調整済みルールベースに勝てない**。
- random 相手でも 0.80–0.87（ルールベースは ~1.0）＝時々自滅。lucario_v2/dragapult には完敗。
- 速度: one_ply ~0.13s/game(max 0.23s), turn_rollout ~0.6s/game(max 1.1s)。10分/試合制限には余裕だが遅い。

## 診断（なぜ弱いか）
1. **評価関数 V() が粗い**: エネルギー充足・攻撃到達可否・打点とKO閾値・タイプ相性・進化見込みを見ていない。
   サイド差/HP差だけでは「良い盤面」を表現できず、ルールベースの精緻なカード個別知識に劣る。
2. **相手モデルが無い**: determinization が相手を Snorlax/エネで穴埋め。「自ターン末」評価は相手の応手・反撃を無視。
   1-ply は特に「今サイドを取れる手」を過大評価しがち（その後返り討ちを見ない）。
3. **ターン内の多段選択の計画性が無い**: 各選択を独立 argmax するため、セットアップ→攻撃の一貫した手順を組めない。

## 学び / 示唆
- **Search API 統合は成功**＝ exp004(RL/MCTS) の土台が出来た（determinization, rollout, 状態評価の足場）。
- 手製ヒューリスティックで強ルールベースを超えるのは非効率。**強さの本命は (A) 学習した価値関数を使う MCTS（公式サンプル路線, 要GPU）か、(B) ルールベース自体の改良**。
- 公式の「ルールベース単体では上位困難。先読み/適応が必要」という主張と整合。ただし**素朴な先読みも単体では不十分**で、価値推定の質が鍵。

## 次アクションの選択肢
- (A) exp004: 公式 RL/MCTS サンプルを動かし、学習価値関数＋MCTS（この exp003 の Search ラッパーを流用）。要 GPU 確認。
- (B) exp003b: V() を大幅強化（エネルギー/打点/KO閾値/相性）＋相手の最善反撃を1手読む（min-max 1.5-ply）。
- (C) ルールベース改良路線（lucario_v2 の構造に打点計算等を追加）。公開 V2 がロジック改良で +26 した実績あり。

## 出典
- Search API 使用法: 公式 RL/MCTS サンプル（`references/raw/official_notebooks/`）。
- 対戦相手・バー: exp002（`workspace/exp002_baselines/`）。
