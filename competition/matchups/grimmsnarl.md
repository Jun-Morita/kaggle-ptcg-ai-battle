# Marnie's Grimmsnarl ex（ex主力・高速）

fine_classify キー: `"Marnie's Grimmsnarl ex"` / デッキ: `workspace/exp028_debauchery/grimmsnarl_deck.json`（実LB #1 Debauchery抽出）
piloting: 自前汎用方策（`P.make_agent(grim)`, revenge_policy系を相手デッキで実行）

## 構造的事実
- 実ラダー #1「Debauchery」（Grimmsnarl ex rush）の正確な複製デッキ。
- exp028で v012 が複製に対して **0.68** と判定 → 対策不要（脅威ではない）と結論済み。差は「マッチアップ」でなく「一貫性」（我々の実力差はレース相性でなく安定運用の差）。

## 我々の勝率履歴
| 版/施策 | 対Grimmsnarl勝率 | 出典 |
|---|---:|---|
| v012（exp028時点） | 0.68 | exp028 SESSION_NOTES |
| v014 turn-beam（2026-07-10, n=100, 生成側は汎用方策の複製操縦） | **0.60**（-0.08 vs v012） | 本ファイル、この場で実測 |

field battery（ex_lucario/dragapult/archaludon/mirror_chq/crustle）には含まれていないため、v013以降の継続計測は手薄。**次に更新する際は field battery に追加するか検討**。

## ⚠️ 2026-07-10 重要アップデート: 新LB#1 Yushin Itoがこのデッキに乗り換え
これまで同一アーキタイプ(Hop's Trevenant非ex)の好敵手としてスカウトしていた
**Yushin Ito（LB#7→#1, 1097.2→1272.8）が、我々と同型の非exデッキから
このMarnie's Grimmsnarl exデッキに乗り換えていた**（sub 54360530, n=1000リプレイ全数で確認）。
乗り換え後の実戦成績（確定値、n=1000フルサンプル）:

| 対戦アーキタイプ | Yushinの勝率 | n |
|---|---:|---:|
| dragapult | **0.92** | 26 |
| lucario_ex | 0.80 | 61 |
| mixed_ex4 | 0.72 | 69 |
| non_ex_attackers（**我々の型**） | **0.71** | 251 |
| mixed_ex3 | 0.64 | 196 |
| mixed_ex1 | 0.63 | 199 |
| mixed_ex2 | 0.62 | 13 |
| ex_beatdown | 0.54 | 28 |
| **crustle_control** | **0.26**（112敗/153戦） | 153 |

**非exアタッカー（我々の型）に0.71で勝ち越す**一方、**crustle_control（壁デッキ）には0.26と大敗**
——三すくみの一角として、Grimmsnarl exが非exを食い、Crustleが Grimmsnarl exを食う構造が
大サンプルで確定。dragapult(0.92)・lucario_ex(0.80)にも強く、現メタで最も広く勝てる型の
ひとつ。v014のこのデッキへの実測(0.60)は**我々の汎用方策による複製操縦**が相手であり、
Yushin本人の卓越した操縦（#7→#1に押し上げた実力）と対戦した場合はより厳しい可能性が高い
（「操縦が#1レバー」という既存knowledge, [[meta-and-leaderboard]]と整合）。

## 適用済みルール
- なし（v012時点で対策不要と判定済みだが、上記アップデートにより**再検討の余地あり**）。

## 未解決の論点
- v013以降のバージョンで継続的に計測していないため、最新のturn-beam/応手ガードでどう変化したか
  今回v014で実測(0.60)。**field batteryへの追加を検討**（新LB#1のデッキであり、我々の型への
  勝率0.71という直接的脅威が確定したため優先度を引き上げるべき）。
- `analyze_adaptation.py`/`policy_diff2.py`はYushinのデッキ乗り換え後は前提が崩れて
  使えない（対象プレイヤーが我々と同アーキタイプである前提が破綻し、target/opponent判定が
  逆転する。試行結果と教訓は`workspace/exp011_meta_watch/scout_yushin_0710.md`と
  memory `meta-and-leaderboard`のツーリング注記に記録済み）。同型デッキを使う別の
  上位者を探すか、我々自身がGrimmsnarl exを操縦する側で分析する必要がある。
