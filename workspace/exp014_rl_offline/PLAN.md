# exp014_rl_offline — 設計 PLAN（深層学習方策 v2）

## 0. 一文
過去の RL 3重ネガティブの真因＝**value ネットの品質**（[[rl-status]], exp010）。その value を
**ヒューリスティック自己対戦**で学んでいたのが間違い。本実験は **トップランカーのリプレイ
（ヒューリスティックより強いプレイの実勝敗ラベル付き軌跡）** で value を較正してから探索/学習に進む、
**オフライン・ファースト**の再設計。

## 1. 前提（確定事実）
- 環境: RTX 3060 12GB + 16 論理コア（WSL2）。エンジンは ~10ms/game の **CPU 実行**。
  → 律速は **GPU FLOPS でなく CPU ロールアウト・スループット**。GPU は小ネットには余る。
- リプレイ JSON（実測, `episode-*-replay.json`）:
  - top: `rewards: [-1, 1]`（最終勝敗）, `steps`（148 step 例）。
  - step[i][agent] = `{observation(POV obs_dict), action(list[int]), reward, status, info}`。
  - 手番側のみ `status=="ACTIVE"` で action 非空（policy_diff で確認済み）。
- 既存資産: DL/解析（`exp011/{analyze,top_meta,extract_deck,meta_watch}.py`,
  `exp013/policy_diff.py`）、BC/特徴量（`exp006`, `exp010/bc_phase1.py`）、
  belief 決定化＋PIMC（`exp008/{belief,agent_pimc}.py`）、deck-dispatch 方策（`exp013/router_policy.py`）。
- 戦略フレーム: [`references/knowledge/ptcg_strategy.md`](../../references/knowledge/ptcg_strategy.md)
  （prize trade / tempo / prize liability）。**方策に焼かず value の補助教師＋特徴量にのみ使う**。

## 2. なぜこの設計なら過去の壁を越え得るか
| 過去（exp010）の壁 | 本設計の対処 |
|---|---|
| value 教師がヒューリスティック上限 | **実勝敗ラベル（上位プレイ）で value を教師あり較正** |
| self-play ラベルが崩壊/偏り | self-play の**前に**オフラインで value を接地。online は league＋gating |
| 探索を増やすと悪化（value が嘘） | go/no-go で「value が当たる」を**先に**実証してから探索に載せる |
| 相手モデルが placeholder/oracle（exp008） | リプレイのカード頻度から**相手デッキ事前分布を学習**＝提出時も探索が活きる |
| 三すくみで方策が循環 | **league/population**＋固定アンカー常駐（非推移性対策） |
| デッキ⊗方策 密結合（exp013） | **deck-conditioned 1ネット**（デッキ特徴入力, デッキ=カリキュラム） |

## 3. データ
### 3.1 収集（`dataset_builder.py`）
- 入力: 上位 submission_id 群（`meta_watch`/LB から）。各 episode を巡回。
- 出力レコード（1 decision = 1 行）: `(obs_dict, action, ctx, final_reward, deck_id, side, step_idx)`。
  - value 教師 = その手番プレイヤーの **episode final_reward**（勝1/負-1）。割引は任意（terminal sparse なので
    γ=1 か 軽い γ=0.997 を比較）。
  - policy 教師（BC）= `action`（status==ACTIVE のみ, len(option)>=2 の実選択のみ）。
- 同時に集計: デッキ別出現, **相手カード頻度テーブル**（determinization 事前分布）, ctx 分布。
- 予算: API は 0.25s sleep（exp013 準拠）。まず上位 ~10 選手 × ~30 episode ≈ 300 games から。
  キャッシュは `references/raw/replays/`（Git 管理外）。重複 DL を避ける（存在チェック）。
- リスク/検証: action の area/index 復号は `policy_diff.decode` を再利用。obs スキーマの版差に注意
  （`schema_version` を記録）。leakage 防止のため **episode 単位で train/holdout split**（同一試合の手を跨がせない）。

### 3.2 特徴量
- exp006/exp010 の特徴量を基盤に、strategy レンズの数値を追加:
  自他プライズ数, 自他ベンチ多サイドポケ数(prize liability), 手札枚数, 場のエネ, 今ターン攻撃フラグ(tempo)。
- デッキ条件: 自デッキの 60枚 multi-hot（or 主要カード embedding）を入力に連結 → deck-conditioned。

## 4. モデル
- 共有エンコーダ → 2 ヘッド:
  - **value head**（主）: 勝敗回帰（tanh, MSE or BCE）。
  - **policy head**: 合法 option 上の分布（BC + 後段 RL の prior）。
- **補助ヘッド（aux, value 安定化）**: 次の量を予測（strategy 教師）:
  プライズ差(終局), あと何ターンで決着, prize-liability。→ 表現学習を助け value のサンプル効率を上げる。
- 小ネット（MLP/小Transformer）。3060 で余裕、CPU ロールアウトが律速。

## 5. 学習段（順序が重要）
1. **value 較正（オフライン教師あり）** ← go/no-go の本体。self-play なし。
2. **BC warm-start**（policy head を上位プレイで初期化）。
3. **online 微調整**: MCTS（探索 API + 較正 value, rollout でなく value 評価）＋
   **league self-play**（過去版プール＋固定アンカー {lucario_v2, Crustle, v008, 上位デッキ}）。
   経験リプレイ＋checkpoint gating（exp010 Phase3 の崩壊対策を継承）。
4. **deck-conditioned 拡張**: charmq 非ex → 複数デッキへカリキュラム拡大。

## 6. ★ go/no-go（第1マイルストーン, 安価・決定的）
> **問い: 上位リプレイで学習した value ネットは、hold-out 試合の勝敗を当てるか？**
- 指標: hold-out（episode split）での
  (a) 終局近傍の勝敗 accuracy, (b) 中盤(step 50%)時点の勝敗 AUC, (c) 較正（reliability）。
- 合格ライン（暫定）: 中盤 AUC **≥ 0.70**（ランダム 0.5, 終局 ~1.0 は自明）。中盤で盤面から
  勝敗の趨勢が読めること＝探索に載せる価値がある証拠。
- **不合格なら RL 路線を誠実に終了**（value が学習不能＝探索の土台なし）。レポートに「実データでも
  value が当たらない」という強い誠実ネガティブとして記載。ROI を見て撤退。

## 7. 提出ゲート（合格後のみ）
- 必須: **stock lucario_v2 ミラー > 0.55**（exp010 のバー）**かつ** heuristic プール非退行
  （vs ex / Crustle / dragapult が v008 を下回らない）。
- クラッシュ安全＋手番時間キャップ（exp008: per-move ~9s, 10分/試合内）。
- 満たして初めて `/build-submit`。満たさなければ提出せず誠実に記録。

## 8. マイルストーン / 成果物
| # | 成果物 | 完了条件 |
|---|---|---|
| M0 | `dataset_builder.py` ＋ データセット（≥300 games） | (obs,action,reward,deck) 行＋相手頻度表＋episode split |
| M1 | `value_calib.py`（学習＋hold-out 評価） | §6 の AUC/accuracy/calibration を report。**go/no-go 判定** |
| M2 | `bc_warmstart.py` | policy head が上位 action を BC（精度 report） |
| M3 | `mcts_value.py`（探索 API＋value）＋ league self-play | ミラー > 0.55 を狙う |
| M4 | 提出（§7 ゲート通過時のみ） | `/build-submit`＋承認 |

各段で SESSION_NOTES に仮説・変更・結果・出典。**負の結果も誠実に記録**（レポートの再現性軸）。

## 9. リスク / 留意
- リプレイ obs は**手番側 POV のみ**＝相手の隠れ情報は見えない（belief/determinization が必要な理由と整合）。
- 上位の action 模倣（policy）は勝率に直結しない（exp013 で実証: ミラー対称, 乖離も等価に good）。
  → **policy は warm-start に留め、勝率の源泉は value+探索に置く**（焼き込みは上限の罠）。
- API レート/容量: DL を分割・キャッシュ。`schema_version` の版ズレを監視。
- 計算: GPU でなく CPU 並列ロールアウトを埋める設計（multiprocessing で 16 コア活用）。
- 撤退規律: M1 不合格なら即終了。ラダー主力は v008（deck-dispatch）を維持。

## 10. 出典 / 関連
- 真因と過去設計: `workspace/exp010_rl_v2/SESSION_NOTES.md`, [[rl-status]]。
- 相手モデルの価値（対照実験）: `workspace/exp008_belief/SESSION_NOTES.md`。
- deck⊗pilot 密結合・意思決定 diff: `workspace/exp013_router/SESSION_NOTES.md`。
- 戦略フレーム: `references/knowledge/ptcg_strategy.md`。
