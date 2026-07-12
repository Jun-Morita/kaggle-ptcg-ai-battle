# スカウティング追記: Yushin Ito — 非exから Marnie's Grimmsnarl ex への乗り換え (2026-07-10)

## 前回(0708)からの変化
`scout_yushin_0708.md`でスカウトした時点(LB#7, 1097.2, sub 53955703)は我々と同一の
Hop's Trevenant非exデッキだったが、**2026-07-09 07:32に新規提出(sub 54360530)し、
LB#1（1272.8）まで急上昇**。新提出のデッキを1000リプレイから復元した結果、
**Marnie's Grimmsnarl ex「Debauchery」系アーキタイプに完全に乗り換えていた**ことを確認
（exp028で複製・評価済みの同一デッキ、`competition/matchups/grimmsnarl.md`参照）。

デッキ構成（Yushin本人の実プレイ、n=348デッキサンプルから復元）:
Marnie's Grimmsnarl ex x4 / Marnie's Impidimp x4 / Rare Candy x4 / Buddy-Buddy Poffin x4 /
Poké Pad x4 / Lillie's Determination x4 / Dudunsparce x3 / Munkidori x3 / Dunsparce x3 /
Dawn x3 / Spikemuth Gym x3 / Marnie's Morgrem x2 / Boss's Orders x2 / Fezandipiti ex x1 等。

## 対戦アーキタイプ別成績（n=1000, フルサンプル確定値）
| 対戦アーキタイプ | 勝率 | 試合数 |
|---|---:|---:|
| dragapult | **0.92** | 26 |
| lucario_ex | 0.80 | 61 |
| mixed_ex4 | 0.72 | 69 |
| **non_ex_attackers（我々の型）** | **0.71** | **251** |
| mixed_ex3 | 0.64 | 196 |
| mixed_ex1 | 0.63 | 199 |
| mixed_ex2 | 0.62 | 13 |
| ex_beatdown | 0.54 | 28 |
| **crustle_control** | **0.26**（112敗/153戦） | 153 |

**非exアタッカー（我々の型）に0.71で勝ち越す**一方、**crustle_control（壁デッキ）には
大敗(0.26)**。三すくみ構造（Grimmsnarl ex rush > 非ex攻撃 > 各種ex > Crustle壁 >
Grimmsnarl ex）が大サンプルで確定。dragapult(0.92)・lucario_ex(0.80)にも強く、
まさに現メタで最も広く勝てる型のひとつ。

## 我々の直接対応（この場で実測）
v014(turn-beam)を、我々の汎用方策で操縦したGrimmsnarl exの複製に当てたところ
**wr=0.600(n=100, err=0)**——exp028時点のv012の0.68から低下（turn-beamの探索が
このマッチアップで必ずしも噛み合っていない可能性、または単純なn=100のノイズ）。
**これは我々の生成操縦が相手**であり、Yushin本人の卓越した操縦（#7→#1に押し上げた
実力）と対戦した場合はより厳しい可能性が高い（「操縦が#1レバー」という既存knowledge
[[meta-and-leaderboard]]と整合）。

## analyze_adaptation.py / policy_diff2.py の限界（重要な運用上の注記）
両ツールは「対象プレイヤーが我々と**同一アーキタイプ**を操縦している」ことを前提に、
デッキの並びから対象プレイヤー(target)を判定する（`archetype(deck)==自分のarchetype`で
target indexを決定）。**Yushinがデッキを乗り換えたことで、この前提が崩れ、target/opponent
の判定が逆転する**（`analyze_adaptation.py`は「mixed_ex5(=実際はYushin自身)」を
"opponent"として報告し、値も反転していた: 74-177(wr=0.29)=1-0.71と整合、これは
Yushin視点でなくYushinの対戦相手視点の数値）。

`policy_diff2.py`の決定一致率は**0.254**（前回スカウト時0.24-0.29と近い値だが、意味が
異なる: 前回は「同型デッキでの操縦一致率」、今回は**「我々の政策をYushinの全く別デッキの
盤面に当てはめた場合の一致率」＝deck-mismatch artifactが支配的**（exp028で既に
文書化された限界と同型）。参考情報として、TO_HAND優先度の上位候補（Dudunsparce/
Grimmsnarl ex/Impidimp/Morgrem/Dunsparce/Munkidori）はYushinと我々の生成policyで
概ね同じ順位——共有された候補プールに対する我々の汎用サーチ優先度が壊滅的には
外していないことは分かるが、**我々はこのデッキを使わないため直接のチューニング対象には
ならない**。

## 結論・アクション
1. **主要な発見はデッキ乗り換えそのもの**（LB#7→#1への急上昇の主因）。
2. Grimmsnarl exは現在の標準5マッチアップ評価プールに含まれていない。新LB#1の実デッキで
   あり我々の型への直接的脅威(0.71)が確定したため、**評価プールへの追加を検討**
   （`competition/matchups/grimmsnarl.md`に記録済み、n=200での再測定が次の一手）。
3. decision-diff系のスカウティングツールはYushinの新デッキに対しては使えない
   （デッキが同型の別の強豪プレイヤーを探すか、Grimmsnarl exを使う別の上位者を探す
   必要がある）。
