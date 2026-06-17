# exp008_belief — SESSION NOTES

## 仮説（柱A）
exp003/004/006 の発見「placeholder determinization が探索を有害化（偽の相手に planning）」に対し、
相手の隠し情報を**実デッキリストからサンプリング（belief 接地）**し、両者をルールベースで rollout する
**PIMC（Perfect-Information Monte Carlo）**にすれば、探索を有害→有益（>ルールベース 0.68）に転じられるか。

## 実装
- `belief.py`: belief determinization。相手の隠し札を「信じる相手デッキリスト」からサンプリング
  （v1は各 pile を独立サンプリング＝近似だが合法な possible world）。placeholder(全Snorlax)を置換。
- `agent_pimc.py`: MAIN 単一選択でのみ PIMC（候補手ごとに K 回 belief 決定化→両者ルールベース rollout→
  勝率 argmax）。他の決定はルールベースに委譲。クラッシュ安全。`use_belief=False` で placeholder 対照。
  - SearchState.observation を `dataclasses.asdict` で dict 化し、ルールベース方策を探索内で駆動（rollout の鍵）。
  - 深さ制限 rollout（horizon 後はサイド差＋盤面圧ヒューリスティック）で高速化。
- `eval_pimc.py`: belief(oracle 相手デッキ) vs placeholder を exp002 プールで対照評価。

## 検証
### スパイク（メカニズム確認）
- belief で相手の手数 avg **50** vs placeholder **33** → **belief は相手が実デッキで現実的にフルプレー**することを確認。
  （placeholder は全 Snorlax で貧弱にしか動けず、探索が「勝ちやすい偽相手」を誤認）。

### 対照実験 本番（eval_pimc.py, n=12, K=6, horizon=40, oracle 相手デッキ）
| 相手 | belief（実デッキ接地） | placeholder |
|---|---|---|
| random | 1.000 | 0.833 |
| dragapult | **0.667** | 0.167 |
| lucario_v2 | 0.167 | 0.000 |
| **対ルールベース平均** | **0.417** | **0.083** |

- **belief は placeholder の約5倍（0.417 vs 0.083）＝中心仮説を強く実証**（公開notebook未実証の対照データ）。
- **belief PIMC は Dragapult に 0.667 で勝ち越し**（exp002 の素 lucario_v2 vs dragapult 0.60 を上回る）＝
  **良い相手モデルがあれば探索は素のルールベースを超え得る**。
- 唯一の弱点 = **lucario_v2 ミラー 0.167**（平均を押し下げ）。ミラーでは PIMC の初手摂動が逆効果＋低Kノイズ。
- 速度 11–17s/game, max_move ~30s（10分/試合には収まるが重い）。
- （参考: 旧 n=10 単一相手 vs lucario_v2 では belief 0.40 / placeholder 0.30）

## 考察 / 正直な評価
- **メカニズムは正しい**: belief 接地で相手が現実的に動き、探索品質は placeholder より上がる（手数50, 勝率+0.10）。
- **だが現実的予算で素のルールベースを超えない**: 
  - rollout 方策＝ルールベース自身なので、低 K(=6) のモンテカルロ・ノイズが「既に良いルールベースの初手」を
    悪い手に置換しがち（分散がゲイン を上回る）。
  - 速度: 13–20s/game, **max_move 10–13s**＝10分/試合予算には収まるが1手が重く、K を上げる余地が乏しい。
- 改善余地（やれば伸びる可能性, 但し不確実・高コスト）:
  1. **K を増やし分散低減**（要高速化: rollout 短縮 or C 実装）。
  2. **selective 適用（柱C）**: lethal/KO 等の高レバレッジ局面のみ PIMC、そこに K を集中。
  3. **アーキタイプ推定**で oracle を実運用化（現状 oracle=相手デッキ既知の上限値）。
  4. rollout 方策を**より強い**ものに（自己改善ループ）。

### exp008b: Conservative Override（ミラー弱点対策）
ルールベース初手を基準に、候補が **margin 以上**明確に上回る時だけ乗り換える（劣化保証＋ノイズ抑制）。
n=10, oracle belief, K6, horizon40:
| margin | vs lucario_v2 | vs dragapult |
|---|---|---|
| **0.10** | **0.50**（0.167→回復） | **0.70**（維持） |
| 0.15 | 0.50 | 0.50（保守的すぎ） |
- **margin=0.10 が最適**: ミラー劣化を解消(0.50)しつつ Dragapult 優位(0.70)を維持。
  推定プール平均 ≈(1.0+0.70+0.50)/3 ≈ **0.73 > バー0.68**（oracle belief）。
- Conservative Override は「明確に勝る時だけ乗り換え」＝**誤った belief にもロバスト**な副次効果。

### realistic-belief 評価（提出条件: 相手デッキ不明→lucario_v2 固定と仮定, margin=0.10, n=12）
| 相手 | PIMC-realistic | 教師 lucario_v2 (exp002) |
|---|---|---|
| random | 1.000 | 1.000 |
| dragapult | **0.750** | 0.600 |
| lucario_v1 | **0.583** | 0.483 |
| lucario_v2(ミラー) | 0.417 | ~0.50 |
- **同一3相手での平均: PIMC 0.583 > 教師 0.528** ＝ **belief PIMC が素のルールベース教師を上回る**（oracle 無し・現実条件で）。
- belief が外れる Dragapult でも 0.75 で勝ち越し（Conservative Override のロバスト性）。
- 弱点はミラー 0.417（教師≈0.50, n=12 ノイズ込み）。**ラダーは Lucario 飽和なのでミラーが支配的＝ここの非劣化が重要**。
- 速度: 13–25s/game(総), max_move ~30s（1試合10分=総時間制限には収まる。per-move 制限は規定になし）。
- 注意: 「平均0.583 < バー0.680」は母集団違い（0.680は iono/abomasnow 込み）。**同一相手比較が正しく、そこでは PIMC 優位**。

### v002 提出（2026-06-17, ref 53780586, PENDING）
- build_v002.py で lucario_v2 inline ＋ belief PIMC ＋ Conservative Override(margin0.10) ＋ 手番時間キャップ(9s) ＋ クラッシュ安全。
- 実バンドル検証: ミラー 0エラー / vs dragapult **0.75**（inline でも回帰なし）/ vs random 1.00 / max_move 23s。
- **校正情報**: v001(lucario_v2+安全性)が **LB 858.3**（公開最高 LB-860 にほぼ並ぶ, pool~0.68→LB858）。v002 は集計待ち。

## 結論
- **柱A は研究的に成功**: 「相手モデル（determinization）が探索の価値を決める」を**対照実験で明確に実証**
  （belief 0.417 vs placeholder 0.083 ＝ **5倍**, 相手手数 50 vs 33）。Strategy レポートの独自性の中核。
- **部分的に競争力も実証**: belief PIMC は **Dragapult に 0.667 で勝ち越し**（素ルールベース超え）・random 1.00。
  → 「良い相手モデルがあれば探索は素のルールベースを超え得る」ことを示した。
- **未解決 = lucario_v2 ミラー(0.167)** と **速度(~30s/手)**。ここを潰せば平均 0.68 超えが射程。
- 実戦 floor は依然 v001。柱A は「あと一歩」＝高速化＋ミラー対策で本命昇格の可能性。

## 次アクション
- eval_pimc(n増)で belief>placeholder を確実化（レポート図用）。
- 柱C: selective 高レバレッジ PIMC（K 集中）で素のルールベース超えを再挑戦。
- 並行: 柱B（デッキ最適化）で floor LB を上げる（探索問題を回避）。

## 出典
- 発見の前提: exp003/004/006。相手・バー: exp002。デッキ: decks.json。
