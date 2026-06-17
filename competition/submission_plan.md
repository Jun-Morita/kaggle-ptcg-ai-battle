# Submission Plan — 創意工夫プラン（v1, 2026-06-17）

## 中心仮説（我々の独自性）

> 「このゲームでは素朴な探索/学習が**逆効果**になる。原因は部分観測下の **相手モデル欠落**
> （determinization が相手を placeholder で穴埋め）。これを **belief で接地した探索**に置き換えれば、
> 探索を有害(0.23)から有益(>0.68)に転じられる。」

これは exp003/004/006 で**自分たちが実証した発見**であり、全公開ノートブックが未解決（belief modeling を将来課題として棚上げ）。
ここに踏み込むことが Strategy 評価（Model 70%＝独創性・頑健性）での差別化になる。

## 3本柱（Strategy の3軸に対応）

### 柱A — Belief-grounded ISMCTS（独創性／Model）★最重要
相手の隠し情報を「メタ事前分布＋観測ログ」で推定し、探索を現実の相手に接地する。
1. **アーキタイプ推定**: 観測ログ（相手の場・捨札・既出カード）から、公開4デッキ（Lucario/Dragapult/Iono/Abomasnow）の
   どれかを推定（or 混合確率）。ラダーが Lucario 飽和な事実を事前分布に使う。
2. **belief サンプリング determinization**: placeholder の代わりに、推定アーキタイプの**実デッキ分布**から
   相手の手札/山札/サイドをサンプリングして探索する（ISMCTS）。
3. **相手ターンはルールベースで rollout**: 相手手番を lucario_v2 等の方策で進め、「現実的な反撃」を織り込む。
- 検証: exp004 の MCTS をこの determinization に差し替え、プール平均が 0.23→**>0.68** に転じるか。

### 柱B — メタ攻略デッキ（Deck 20%）
- **prize liability を主指標**に。Mega Lucario ex=3渡し（2KOで負け）＝飽和メタは「強いが脆い」。
- 戦略: (i) Lucario ミラーに勝つ調整 か (ii) **低 liability（非ex/1-prize 主体）でメタを突く**別アーキタイプ。
- fast harness で Lucario 偏重フィールドに対し 200+戦 A/B。prize liability・事故率・進化ライン整合を評価。

### 柱C — 安定したルールベース脊柱＋選択的探索（安定性／Model・Report）
- 既定は強ルールベース(lucario_v2, 0.68)。**高レバレッジ局面のみ**柱Aの belief 探索を発火
  （lethal/KO 可能、攻撃選択など）。素朴な全面探索が有害という発見の実践。
- **クラッシュ安全＋normalize_selection**（optional 文脈で中立手を避ける）で取りこぼしゼロを徹底（安定性は70%評価の構成要素）。
- BC net は高速・頑健なフォールバック／探索の価値ガイドとして温存。

## 提出運用
- Simulation: 5/日・最新2つ採点。**安全な floor（ルールベース+安全性=提出済v001）を常に1枠**確保し、
  もう1枠で実験版（柱A/B）を段階投入。各提出の LB を `submit/` に記録し、ローカル勝率との校正を継続。
- Strategy: Writeup(≤2000語)＋図。中心ストーリー＝「相手モデルがボトルネック→belief接地で解決」。
  図: 強さ序列バー / 探索が有害な実証 / belief 接地後の改善 / prize liability 比較 / マッチアップ matrix。

## 実験ロードマップ
- exp007: デッキ戦略（prize liability＋メタ分析、A/B）。… 柱B
- exp008: belief-grounded determinization（アーキタイプ推定＋実デッキサンプリング＋相手ルールrollout）。… 柱A 中核
- exp009: 選択的高レバレッジ探索（ルールベース脊柱＋belief探索の発火条件）。… 柱C
- exp010: 安定性ハードニング（normalize_selection, DAgger でBC強化, seat/分散分析）。… 柱C
- 各実験の結果を Strategy レポートの節として蓄積。

## リスクと floor
- 柱A は最高 ROI だが不確実（belief 推定の精度・探索コスト 10分/試合）。**floor は柱B+C（ルールベース良デッキ+安全性）で
  既に LB-860 級と競争可能**。柱A が当たれば一気に抜ける、外れても堅実な提出＋良い分析レポートが残る設計。

## 出典
- 発見: exp003/004/006（`workspace/`）。メタ/技法: 公開ノートブック（`references/knowledge/notebooks.md`）。
- 評価基盤・バー: exp002。安全性: exp005（提出済 v001）。
