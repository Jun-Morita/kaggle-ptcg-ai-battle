# 公開ノート分析: Gold(LB~1250) Starmie + Prize Tracking（2026-06-22）

- 取得日: 2026-06-22 / raw: `references/raw/public_notebooks/prize-card-tracking-1250-starmie.ipynb`（Git管理外, 解説1セル＋PrizeTracker コード）
- 著者: Gold メダル圏の Starmie/Froslass rule-based 方策。デッキは ashleysandlin の Limitless リストが元。
- コンプラ: 公開ノート＝利用可（出典明記）。

## 方策アーキテクチャ（トップ事例）
- **Generic mode**（既定スコアリング）＋**Matchup-specific modes**（Lucario/Iono/Crustle 別に攻撃役・技・プライズプラン・
  回復/退却を切替）＋**Finish mode**（リーサル forward-search で「このターン勝てるか」を検証→勝ち筋を再生）。
- 標語: 「**通常ターンはルール、勝ちターンは探索で検証**」。
- → **トップ(1250)が明示的に相手アーキタイプ別へ方策を変えている**。我々の exp018「非ex apex は相手適応でなく規律で勝つ」と
  矛盾せず**併存**＝デッキ次第（Starmie は柔軟な線を持つので matchup mode が活きる）。ユーザー仮説（相手適応）の裏付け。

## ★核心: Prize Tracking が exp015 の失敗原因を解決
- exp015（自ターン正確探索のリーサル補完）の NO-GO 真因＝「探索が**山札にあると誤認した札**で偽リーサルを出す」
  （我々は決定化で**全60リストからランダム抽出**＝**サイド落ち/見えてない札も混入**）。
- 著者は同じ問題を **NOMATCH** と命名（探索が実際にはサイド落ちの札で勝ち筋を作り、本番で再現不能）。
- **解決＝PrizeTracker**（保守的サイド落ち推定, コードは raw 参照, 再利用可）:
  - デッキリスト Counter から**可視札を全減算**（select.deck＝サーチ中の見える山, hand, active/bench＋preEvolution＋
    energyCards＋tools, discard, 自分の stadium）→ 残り枚数 == サイド枚数 なら**それがサイド落ち**。
  - 矛盾（負カウント）や枚数不一致なら **unknown を返す**。原則「**間違った推定はノー推定より悪い**」。
  - **in-flight 札の減算**: 効果解決中（Hilda が手札を離れ discard 未到達）は `obs.select.effect` が指す札も減算
    ＝サーチ解決フレーム跨ぎでも整合（logs は前回選択以降しか持たないので不十分）。
  - taken（サイドを取った）時は logs(PRIZE→HAND)→ 不足なら hand serial 差分で既知サイド集合を更新。

## 我々への活用（重要度順）
1. **exp015 をサイド落ち除外の決定化で再訪**（最有力）: forward-search に渡す your_deck を「全リスト − 可視 − サイド落ち推定」
   にすれば偽リーサルが消え、**検証済みリーサル補完**が機能し得る。exp015 の NO-GO は早計だった可能性
   → 探索系統の結論（[[rl-status]]）を見直す材料。我々の非ex デッキも Poffin/Pad/Pokégear/Hop's Bag/Night Stretcher 等
   山札を見るカードを使うので prize tracking の恩恵あり。
2. **Matchup-specific modes**: 相手アーキタイプ検出→マッチアップ別の優先度（攻撃役/技/プライズプラン/回復）。
   exp018 の discipline（壁ゲート）を一般化する筋。デッキにより有効。
3. **hybrid 設計**（通常=ルール / 勝ち=検証探索）: prize tracking 込みなら exp015 の当初設計が成立。

## 出典
- 公開ノート: prize-card-tracking-1250-starmie（著者 Gold 圏）。デッキ元: ashleysandlin (Limitless)。
- 関連: 我々の [[engine-and-search-api]]（search_begin の hidden info 指定）, exp008 belief 決定化, exp015 tactical。
