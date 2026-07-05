# Dragapult ex（レース・バースト）

fine_classify キー: `"Dragapult ex"` / 3rd-party実装: `workspace/exp020_deckinnov/load_dragapult.py`
(public notebook "phantom-dive-or-go-home-a-dragapult-ex-deck")

## 構造的事実
- Dragapult ex **HP320 / Phantom Dive 200ダメージ（2エネ）** → 我々の主力 Trevenant（HP140）を毎ターン確殺。
- Trevenant revenge-window 130ダメージ → 320を割るには **3発必要**。ベンチ狙撃を絞ってもレース自体で負けている。
- **勝ち筋 = +30補正**: revenge 130 + 30（Choice Band/Postwick等）= 160×2 = **320ちょうど2発**で対応可能（exp034で機構特定）。
- ベンチ狙撃discipline（exp034 gated antispread）は無効: 0.200（対策前と同水準）。**レース算術そのものが機構**であり、ベンチ管理では解決しない。

## 我々の勝率履歴
| 版/施策 | 対Dragapult勝率 | 出典 |
|---|---:|---|
| v011 revenge-window | 0.140 | submissions.csv |
| v012 deck-ratio | 0.155 | submissions.csv |
| v013 応手ガード | 0.205 | submissions.csv |
| v014 turn-beam（+30補正の系列化） | **0.220**（現行最良） | submissions.csv |
| exp034 gated antispread（単独） | 0.200（無効） | exp034 SESSION_NOTES |
| exp038 depth=2（n=100, 全修正後） | 0.10 | exp038 SESSION_NOTES（悪化） |
| exp039 archetype模倣ガード（n=100, ゲート前） | 0.17（v014比 -0.05, やや悪化） | exp039 SESSION_NOTES |
| exp039 + archaludonゲート（n=100, dragapultはゲート対象外） | 0.17（同値、**未改善**） | exp039 SESSION_NOTES 2026-07-05 |

## 適用済みルール
- なし（archaludonのような専用ゲートは未実装）。turn-beamの系列化（v014）が現状のベスト。

## 未解決の論点
- exp039のarchaludonゲートと同様、dragapultも「構造的に厳しい」マッチアップ。応手ガードが同様のノイズで悪化している可能性があり、
  同じ検出→無効化パターンが有効か検証の価値あり。**archaludonゲート適用後もdragapultは0.17のまま不変**＝
  exp039自体が「field total 2.63、v014の2.67比でパリティ」として決着したため（DO NOT SHIP）、
  dragapult専用ゲートの実装は優先度を下げて保留。
- 本質的な勝ち筋（+30補正）は既にpilotingに組み込み済み（revenge_policy.py の REVENGE_BONUS/PRIZE_W）。これ以上の改善はデッキ構成（Choice Band比率など）側のレバーかもしれない。
