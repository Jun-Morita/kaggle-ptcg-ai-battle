# exp004_mcts — SESSION NOTES

## 仮説
公式 RL/MCTS サンプル（AlphaZero 系: Transformer value/policy ＋ MCTS over Search API ＋ 自己対戦学習）
を動かし、学習価値関数で exp002 のバー（プール平均 lucario_v2 = 0.680）を超える。

## 環境
- GPU: RTX 3060 12GB / torch 2.6.0+cu124（`uv pip install torch --index-url .../cu124`）。
- `train_mcts.py`: 公式サンプルを移植（モデル/特徴量/MCTS はサンプル準拠、学習ループを関数化＋パラメータ化、
  エンジン=exp001, デッキ=exp002, 評価=exp002プール接続）。`eval_vs_pool.py`: 学習済みモデルをプール対戦。
- モデル: d_model=128, heads2, ff256, enc1/dec1。チェックポイント ~50MB。

## run1 (generations=5, search_count=16, selfplay=40, eval=20, deck=lucario_v2, seed=42)

学習ログ（対 random, n=20, ノイズ大）:
| gen | vs random | samples | loss | sec |
|---|---|---|---|---|
| 0(未学習) | 75% | 5780 | 0.278 | 183 |
| 1 | 35% | 4732 | 0.194 | 152 |
| 2 | 60% | 3580 | 0.071 | 121 |
| 3 | 65% | 4506 | 0.039 | 167 |
| 4 | 40% | 3607 | 0.036 | 117 |

loss は単調減少だが対 random 勝率は振動・非改善（n=20 ノイズ＋データ過少）。

### exp002 プール評価（n=20/相手, search_count=16）— **NEGATIVE**
| モデル | vs random | vs dragapult | vs lucario_v1 | vs lucario_v2 | 対ルールベース平均 |
|---|---|---|---|---|---|
| gen0(未学習) | 0.400 | 0.050 | 0.000 | 0.050 | **0.033** |
| gen3(学習後) | 0.550 | 0.000 | 0.050 | 0.000 | **0.017** |

- バー 0.680 に遠く及ばず。**デモ規模 AlphaZero は非競争的**。学習はプール成績にほぼ寄与せず。
- 推論コスト: 0.3–0.9s/game, maxmove ~1.8s（10分/試合制限には余裕）。

## 診断（なぜ届かないか）
1. **データ/計算量が桁違いに不足**: AlphaZero は本来 大量自己対戦が必要。約2万サンプル/5世代では
   ルールベースが内包するドメイン知識（カード個別効果・打点・相性）を学べない。
2. **determinization が相手を placeholder（Snorlax/エネ）で穴埋め** → MCTS が「偽の相手」に対して planning。
   強い攻撃型（dragapult/lucario）の脅威を全く読めず完敗（0/20 多発）。exp003 と同根の弱点。
3. cold-start（ランダム初期重み）からの自己対戦は立ち上がりが遅い。

## 学び / 方針転換の示唆
- **パイプライン（自己対戦→学習→評価）は完動**＝資産。だが「公式サンプルをそのまま回す」だけでは勝てない。
- 有望な次の一手（compute 効率が良い順）:
  - **(BC/IL) 模倣学習で warm-start**: 強ルールベース（lucario_v2 等）や公式の上位エピソード export
    （Data ページ記載, 日次提供）を教師に value/policy を事前学習 → その後 RL/MCTS で微調整。
    cold-start より遥かに効率的で、ルールベースの知識を net に注入できる。**本命候補**。
  - **determinization の改善**: 相手を「同種強デッキ分布」からサンプリング、観測済み情報を反映。
  - 探索強化（search_count↑）は計算コスト大・単体では net の弱さを補えない。
- 現実的戦略（Strategy 評価 70% は安定性・独創性も見る）: まず **強ルールベース or BC-net を提出ベースライン**にし、
  その上で「RL/MCTS で○○を改善」という独自性をレポートに載せる方向が、賞金狙いとして堅実。

## 次アクション
1. exp005(BC): lucario_v2 等で自己対戦/対戦ログを大量生成 → (obs→選択) を教師に policy/value を BC。
   → そのまま agent 化してプール評価（ルールベース近傍まで出るか）。
2. BC-net を初期重みに exp004 の RL/MCTS を再開（warm-start）。
3. 並行: 提出パイプライン（submission.tar.gz）を exp005 として整備し、まず lucario_v2 を実提出して LB 校正点を取る。

## 出典
- 公式 RL/MCTS サンプル（`references/raw/official_notebooks/`、要約 `references/knowledge/notebooks.md`）。
- 評価基盤・バー: exp002。Search ラッパー知見: exp003。
