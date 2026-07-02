# exp028 — Debauchery Tea Party (#1 ladder, 1350.5) deck extraction & counter-check

## 動機
LB #1 The Debauchery Tea Party (sub 54176312) のデッキを複製し、v012 が既に勝てているか確認。
勝てていれば新規カウンター不要（工数節約）、負けていれば piloting/deck 対策を検討。

## 抽出結果
`extract_deck.py 54176312` — **620/620 全試合で同一デッキ**（archetype=mixed_ex5, ex=5枚）。
Marnie's Grimmsnarl ex ラッシュ:
- 攻撃: Grimmsnarl ex×4(Rare Candy 進化), Impidimp×4/Morgrem×2, Munkidori×3, Fezandipiti ex×1, Budew×1, Yveltal×1
- draw: Dudunsparce/Dunsparce×3+3
- engine: Rare Candy×4(turn2立ち上げ), Buddy-Buddy Poffin×4, Poké Pad×4, Lillie's Determination×4, Dawn×3
- stadium/tech: Spikemuth Gym×3(闇タイプ強化), Boss's Orders×2, Tool Scrapper/Hero's Cape/Xerosic's Machinations/Risky Ruins 各1
- energy: Basic {D}×10 のみ（特殊エネなし）

→ `grimmsnarl_deck.json` に保存。

## 評価（eval_grimmsnarl.py, n=200）
**v012（v_trev デッキ＋v011 revenge policy） vs Grimmsnarl-ex（generic pilot）＝ wr 0.680 (136-64-0), err=0。**

## 結論
- **構造的な弱点なし。既に有利（0.68）**。新規カウンターデッキは不要。
- 注意: 相手側は generic pilot（我々の他デッキ検証と同じ慣習）で操縦しており、Debauchery 本家の実際の
  操縦（turn2 Rare Candy 立ち上げの精度など）は未反映＝実際の差はこれより縮む可能性あり。
  致命的な弱点があるなら generic pilot でも露呈するはず＝**低リスクの朗報**と解釈。
- 示唆: LB #1 が我々に対して優位（1350 vs 815）なのは、単一マッチアップの弱さではなく
  **収束速度・スループット・全方位安定性**（exp022 の take-when-legal 結論と整合）。
  deck-counter レバーではなく、既知の「pilot天井 / 比率天井」を超える必要がある構造的課題。

## 次候補
- Debauchery の実際の操縦をリプレイから覗く（turn2 Rare Candy の判断基準、Spikemuth Gym の張り替えタイミング等）→
  `/scout-top` で具体的な方策チューニング標的を探すのが筋が良さそう。
