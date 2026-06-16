# exp004_mcts — PLAN（GPU 空き待ち中の準備）

## 仮説
公式 RL/MCTS サンプル（AlphaZero 系: Transformer value/policy ＋ MCTS over Search API ＋ 自己対戦学習）を
動かし、学習価値関数を得れば、exp002 のルールベースのバー（プール平均 lucario_v2 = 0.680）を超えられる。
exp003 の負の結果（手製ヒューリスティック先読みは 0.21–0.27）に対し、本路線は価値推定の質をデータで上げる。

## 前提・制約
- GPU: RTX 3060 12GB（CUDA 13.1 driver）。現在 別プロセスが専有中 → **空き待ち**。
- torch 未導入。空いたら `uv pip install torch --index-url https://download.pytorch.org/whl/cu124`。
- モデルは小さい（公式: d_model=128, encoder1/decoder1層）。CPU でも pipeline 検証は可能、本学習は GPU。
- エンジンは CPU（ctypes）。自己対戦の律速は engine + MCTS のステップ数。1試合10分制限あり（本番）。

## 設計（公式サンプルをベースに、exp001/003 の資産を流用）
1. **特徴量**: 公式の `SparseVector` + `EmbeddingBag`（盤面/手札/自デッキ/スタジアム/ターン）。encoder=value, decoder=policy。
2. **MCTS**: `search_begin/step/end`（exp003 の determinization・rollout 足場を流用）。PUCT (c=0.4·√visit)、最多訪問選択。
3. **determinization の改善余地（exp003 知見）**: 公式は相手を Snorlax/エネで穴埋め＝相手モデル無し。
   - v1: まず公式どおりで pipeline を通す（再現第一）。
   - v2: 相手の観測済み情報（捨札・場・既知サイド）と「相手も同種デッキ分布」を使ったサンプリングに改善。
4. **自己対戦 → 学習**: TD(λ=0.9) で value ラベル、Huber 損失で value/policy。世代ループ。
5. **デッキ**: まず lucario_v2 デッキ固定（exp002 最強・バー基準と揃える）。将来デッキ最適化は別 exp。

## 評価（exp002 と同一基準で比較可能に）
- 学習済みモデルを `agent(obs_dict)` 化（MCTS 推論）。
- exp002 のプール（dragapult/iono/abomasnow/lucario_v1/lucario_v2/random）と対戦し平均勝率。
- **合格ライン: プール平均 > 0.680**。途中世代の対 random / 対 lucario_v2 winrate を学習曲線として記録。
- 推論コスト（1手の最大思考秒）も計測（本番10分/試合の予算管理）。

## 実行手順（GPU 空き次第）
1. `uv pip install torch --index-url https://download.pytorch.org/whl/cu124`、`uv run python scripts/check_gpu.py` で torch GPU 確認。
2. 公式サンプルを `train_mcts.py` に移植（パラメータ化: SEARCH_COUNT, 世代数, バッチ, デッキ）。
   - 公式サンプル本体は競技提供物 → 逐次コピーは gitignore、我々の改変コードは tracked。
3. **CPU/小設定でスモーク**（自己対戦 数戦＋1ステップ学習が回るか、エラーなく動くか）。
4. GPU で短時間学習（数世代）→ `agent` 化 → exp002 プールで評価（n=30〜）。
5. determinization v2・SEARCH_COUNT 増・モデルサイズ等をチューニング。
6. 結果を SESSION_NOTES / daily_report に記録。バー超えたら提出パッケージング（exp005）へ。

## リスク / 留意
- 自己対戦は遅い（MCTS×engine）。SEARCH_COUNT と世代数のバランスで wall-time 管理。
- 相手モデル無しの determinization は強さの上限になりうる（exp003 の教訓）。早めに v2 を検討。
- GPU 共有のため OOM 注意（モデルは小さいが他プロセスと競合）。
- 提出時は学習済み重みを同梱（容量・ロード時間）。本番のネット/時間制限を確認。

## 参照
- 公式 RL/MCTS サンプル要約: `references/knowledge/notebooks.md` / raw: `references/raw/official_notebooks/`。
- Search ラッパー・determinization: `workspace/exp003_lookahead/agent_lookahead.py`。
- 評価基盤・バー: `workspace/exp002_baselines/`（matchups.json）。
