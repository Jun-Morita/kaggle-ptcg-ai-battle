# exp057 — 公開1034.6 Alakazam（search-augmented）の取り込み・評価・v025候補化

## 出典・安全レビュー
- Kaggle公開notebook `tientrum/search-augmented-heuristic-agent-alakazam`（07-13公開）。
  チームの旧チェックポイントで、**その提出自体が07-05に実ラダー収束値1034.6を記録**（ピークでなく収束値）。
- 構造: 手調整＋memetic探索で磨いた重み表（WEIGHTS）＋**2-ply信念サンプリング探索**
  （search_begin API、ヒューリスティック上位K候補のみ展開、決定化数本）。
- 安全レビュー合格: import os/json/cg.apiのみ。`eval(`は全て自前`_leaf_eval`。`open()`は
  deck.csv（/kaggle_simulations fallback付き＝bare-exec安全設計）と任意alak_w.jsonのみ。
  ネットワーク・subprocess・動的実行なし。

## 測定（n=200 CRN, err=0）
1. **v023-koff vs pub1034 = 0.670**（n=20の0.55は小標本ぶれ）。
   → 実戦alakazam 0.48の残差はこの公開パイロットでも埋まらない（場の私的改変が上）。
2. **候補評価（9相手×両帯域）: 自帯域0.7995 / silver帯0.8536**（v023: 0.648/0.792）
   - 強み: 純壁0.910（LOキラー狩り）・archaludon 0.865・alakazam系0.89-0.91・marnie 0.93・lucario 0.90
   - 弱み: crustle_LO 0.375・dragapult 0.360
   - caveat: プールのalakazam枠は弱い代理なので0.905は楽観。ただし実ラダー1034.6が上位証拠。

## 出荷ゲート（全通過）
- ビルド: `build_pub/submission.tar.gz`（クラッシュ安全ラッパー、deck.csv同梱）
- スモーク n=30×3: lucario 0.933 / crustle 0.867 / dragapult 0.567、0エラー
- bare-execレプリカ: 193手・0エラー・**max_act 0.32s**（探索スパイク込みで1s制約に余裕）

## 提出判断（ユーザー承認待ち）= v025候補
- 論点: eligible={v023 927(古枠), v024 708(新枠)}。**今提出するとv023(高い方)が押し出される**。
  - 案A: 即提出（1034.6の実証を信じてv023を犠牲に）
  - 案B: v024がv023近くまで収束するのを待ってから提出（927の保険を守る、締切8/16に余裕）
- リスク: 07-05以降のメタずれ（Alakazamミラー飽和・Enhanced Hammer合戦）、
  現#1 Majkelも同系（ミラー0.54でしか勝てない相手）。
