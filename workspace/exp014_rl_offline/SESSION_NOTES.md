# exp014_rl_offline — SESSION NOTES

設計は `PLAN.md`（オフライン・ファースト RL: 上位リプレイの実勝敗で value 較正 → go/no-go → 探索/league）。

## M0: dataset_builder（2026-06-21）完了
仮説: 過去 RL の真因＝value 品質（[[rl-status]]）。value 教師をヒューリスティック自己対戦でなく
**トップランカーのリプレイ（実勝敗ラベル付き強プレイ軌跡）**にすれば較正できる。その教師データを構築する。

### 実装（`dataset_builder.py`）
- 入力: submission_id 群（明示 or `--seed <sub>` で対戦相手を自動ハーベスト）。
- リプレイ実測スキーマ: top `rewards:[-1,1]`、step[i][agent] = `{observation(POV obs), action, reward, status}`。
- 抽出: 手番側 `status==ACTIVE` かつ `select!=None` の各局面を1記録。**60-option=デッキ選択ステップは除外**。
  - value 教師 = その手番プレイヤーの **episode 最終 reward**（win+1/loss-1）。
  - policy(BC) 教師 = `action`（`is_choice` = nopt>=2 かつ count 妥当）。
  - obs(~1-6KB) を埋め込み → M1 を自己完結化。
- 同時集計: deck_id→60枚（`decks.json`）、相手カード頻度（`opp_cardfreq.json`＝determinization 事前分布）、
  ctx 分布、value バランス。
- **leakage 防止**: episode_id ハッシュで train/holdout を **試合単位** split（同一試合の手を跨がせない, holdout 20%）。
- 出力: `results/{records.jsonl, decks.json, opp_cardfreq.json, manifest.json}`（全て gitignored）。

### 結果（`--seed 53858964 --top 8 --max-eps 40`）
- **319 episodes（holdout 62）/ 25,563 records（choice 19,619）**。
- **value バランス: win 13,424 / loss 12,139**（ほぼ均衡＝go/no-go の AUC 評価に好適）。
- ソース 8 subs（charmq の対戦上位）/ **6 デッキ** / 相手カード 186 種。
- ctx 分布: MAIN 13,668 / TO_HAND 3,357 / ATTACH_FROM 2,517 / ATTACH_TO 2,045 / DISCARD 822 / …
- データ量: records.jsonl **161M**、replay キャッシュ 1.3G（references/raw, gitignored）。

### 留意 / 次への申し送り
- value ラベルは「その局面のプレイヤーの最終勝敗」。**序盤の勝者局面も win ラベル**＝これは想定通りで、
  go/no-go は「中盤盤面から勝敗趨勢を当てられるか(AUC≥0.70)」を測る設計（PLAN §6）。
- **デッキ多様性は6種**（8 subs が少数アーキを使用）。value 較正(盤面→勝敗)には十分だが、後段の
  deck-conditioning 拡張時は seed/subs を増やして多様化する。
- obs スキーマ版は records 各行に保持せず（必要なら `schema_version` を後で付与）。今回は単一コンペ・短期間で版差なしと仮定。
- M1 で features(obs)→value を学習。特徴量は exp006/exp010 ＋ strategy 数値（prize差/tempo/liability, PLAN §3.2）。

## M1: value 較正 go/no-go（2026-06-21）→ **NO-GO（決定的）**
仮説: 上位リプレイの実勝敗で value を学習すれば、中盤(phase 0.4-0.6)の勝敗を AUC≥0.70 で当てられる
（＝探索の土台ができる）。これが RL 路線の生死を決める分岐。

### 実装
- `value_calib.py`: obs→**strategy-lens スカラー17個**（prize差/active HP・エネ/盤面エネ/bench/手札・山枚数/
  turn/先攻/相手状態）→ 小MLP。episode 単位 holdout（leakage なし）。AUC/phase別/Brier。
- `value_calib_rich.py`: 上記＋**カードレベル embedding**（手札の中身＋自他盤面 card-id を EmbeddingBag で pool）。
  ※ obs は手番側の **手札中身が 2985/3002 記録で利用可能**（前回 handCount だけだったのを是正）。

### 結果（holdout 5295, test win-rate 0.469）
| 特徴量 | train AUC | test AUC | **中盤AUC(0.4-0.6)** |
|---|---|---|---|
| スカラー17 | 0.912 | 0.688 | **0.637** |
| ＋カードレベル(手札+盤面) | **0.999** | 0.684 | **0.585** |
| baseline (prize_diff 単独) | — | **0.688** | — |
- phase別(rich): 序盤0.66 / 中盤0.58 / **終盤0.80**。スカラーも同様の勾配。
- **VERDICT: NO-GO（中盤 < 0.70, 2特徴量で一致）**。

### 結論（誠実なネガティブ・4本目で決定的）
- カードレベル特徴(手札中身含む)を足しても test 改善せず＝**特定試合の丸暗記**(train 0.999)で汎化しない
  （6デッキ319試合では embedding 過学習）。スカラー(暗記不可)も 0.637。
- **prize 差が唯一の汎化信号**。終盤(0.80)は当たるが**中盤(探索が効くべき場所)は当たらない**。
- → **exp010「探索を増やすと悪化」を機構的に説明**（中盤の無情報 value を MCTS が増幅）。PTCG 中盤の
  高分散はゲーム固有（運・ドロー）でモデル不足ではない。
- → **value 較正という unblocker は実データで失敗**＝deep-RL/MCTS 路線は「未試行」でなく**経験的に上限**。
  [[rl-status]] 4本目。GPU をこれ以上 value 較正に費やさない。

### 申し送り（撤退規律, PLAN §9 通り）
- M2/M3（BC warm-start, MCTS+league）は**着手しない**（土台の value が中盤無情報のため ROI なし）。
- 路線: **heuristic v008 ＋ /meta-watch ＋ Strategy レポート**。
- 再利用資産: オフライン pipeline（`dataset_builder.py`＝4種教師抽出, `value_calib*.py`＝較正評価, AUC自前実装）。
  相手カード頻度表（determinization 事前分布）も保存済み。
- レポート素材: 「実データ・2特徴量でも中盤 value は AUC<0.70」＝再現性・誠実さ軸の核（exp008/exp010 と接続）。
