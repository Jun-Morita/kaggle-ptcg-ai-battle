# exp020_deckinnov — SESSION NOTES

目的: デッキ革新（自前構築の独創デッキ）。Strategy Deck Score(20%)＋独創性が主価値。制約＝deck⊗pilot 密結合。

## カードプール・スカウト（`scout_cardpool.py`）
- 非ex の **1エネ高火力攻撃が多数未活用**（Tinkaton 240, Ceruledge 220, Decidueye 170, Palafin 130 …）。
  多くは条件付き or S2。named エンジン families: Team Rocket65 / N18 / **Hop14(現用)** / Ethan10 / Cynthia / Iono …。
- 我々の Trevenant(1エネ・S1・スケーリング)と同 archetype＝方策が回せる可能性のある候補を抽出。

## 試作: Tinkaton アンチ・ミラー（exp020）→ ★失敗（誠実な負）
- 概念: **Windup Swing 240 − 60×相手activeエネ**＝低エネ(非exミラー=我々の弱点)に高火力、ex に減衰＝**ミラーを構造的に狙撃**。
- `tinkaton_deck.json`（Tinkaton 697/698/699 ライン＋Rare Candy/Poffin/Ultra Ball/Poké Pad/Pokégear/Carmine/Lillie/Boss/
  Choice Band＋Metal 15）。`tinkaton_policy.py`（条件ダメージを plan で計算, Metal 弱点, search 優先度）。
- 結果（built artifact, 0 err）: **vs v009 ミラー 0.000(0-20)**, vs ex 0.10, vs Crustle 0.15, vs dragapult 0.05。全敗。
- **原因＝セットアップ不全**: **S2 ライン(Tinkatink→Rare Candy→Tinkaton)を我々の pilot が組み立てられず**、
  S1 Trevenant(1エネ・即攻撃)にレースで完敗(avg_moves 121=遅い)。**deck⊗pilot 密結合が S2 で再発**(Debauchery TR engine 0.167 と同型)。
- 概念(アンチ低エネ)は理論的に妥当だが、**S2 は我々の generic+patch pilot では遅すぎて回らない**。

## 学び / 結論
- **独創デッキは『回せる line』が必須**: 基本/S1 の即攻撃ラインでないと、generic+patch pilot では setup 不全でブリック。
  S2 線(Tinkaton)は Rare Candy 手順の専用操縦が要り、しかも S1 ミラーに速度で負ける＝二重苦。
- deck⊗pilot 密結合を**4例目で再確認**（v006 charmq○ / Debauchery TR✗ / Alakazam(他者実装)○ / Tinkaton S2✗）。
- **現実解**: 我々が回せる非ex(S1 Trevenant)が引き続き最良。デッキ革新でミラーを覆すには、(a) S1/基本の
  アンチ低エネ攻撃を探す or (b) Tinkaton 専用の高度な setup pilot を書く（高コスト・速度問題は残る）。
- レポート価値: 「カードプール上は強い 1エネ攻撃が多数あるが、**pilot 可能性(line の速さ・複雑さ)が制約**＝
  なぜ我々が S1 非ex を選ぶか」を実証した（Deck 章＋deck⊗pilot 主張の補強）。

## 強 Dragapult ex（公開ノート）の脅威＆メタ適合 実測（2026-06-23）
- 公開「Phantom Dive」Dragapult を抽出・安全レビュー（純 rule-based）・評価相手化（`load_dragapult.py`, `eval_dragapult.py`）。
- 結果（n=40, built v009 vs module dragapult ほか, err 0）:
  | 強 Dragapult vs | 勝率 |
  |---|---|
  | **v009 非ex（我々）** | **0.775**(31-9) |
  | lucario_ex | 0.400 |
  | Alakazam | 0.500 |
  | crustle(v004) | 0.000 |
  | **weighted(現メタ87%)** | **0.474** |
- **結論**:
  1. **脅威確定**: 強 Dragapult は v009 を **0.775** で狩る。exp017 の「Dragapult 0.19」は**弱baseline pilot**が原因＝
     **deck⊗pilot をピロット品質差で実証**（弱pilot 0.19 / 強pilot 0.775 vs 我々）。
  2. **だが現メタで Dragapult 不利**(0.474<0.50): ex(39%)に 0.40、Crustle(11%)に **0.000**(Dragapult **ex** の damage を
     Safeguard が無効)で沈む。**ex 復権中の今は三すくみが Dragapult を抑える**＝我々の v009 は当面安全。
  3. **ピボット非推奨**（v009 ~0.59-0.64 ＞ Dragapult 0.474）。exp017 の不提出を**正しい理由(メタ・タイミング)で**確定。
  4. **改善 ROI 低**: Crustle 0.0/ex 0.40 は構造的(ex-immunity, 高HP ex を spread で取り切れない)＝agent 改善でなく
     非ex 攻撃追加＝別デッキが必要。価値は脅威の実測。
- **監視事項**: メタが単サイドへ戻れば Dragapult が脅威化 → `/meta-watch` で Dragapult share を注視。

## 再利用資産
- `scout_cardpool.py`（任意 min_dmg で非ex 攻撃候補＋メタ採用フラグ＋engine families）。
- 試作枠組み（deck.json＋pilot patch＋build/smoke/mirror eval）。`load_dragapult.py`（強 Dragapult 評価相手）。
