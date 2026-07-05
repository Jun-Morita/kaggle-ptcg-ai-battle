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

field battery（ex_lucario/dragapult/archaludon/mirror_chq/crustle）には含まれていないため、v013以降の継続計測は手薄。**次に更新する際は field battery に追加するか検討**。

## 適用済みルール
- なし（対策不要と判定済み）。

## 未解決の論点
- v013以降のバージョンで継続的に計測していないため、最新のturn-beam/応手ガードでどう変化したか未確認。優先度は低い（既に安全マージンがある）。
