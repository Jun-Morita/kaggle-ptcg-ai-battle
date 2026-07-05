# Mega Lucario ex + Solrock/Lunatone（ex主力）

fine_classify キー: `"Mega Lucario ex + Solrock/Lunatone"` / 自前実装: `workspace/exp007_anti_crustle/anti_crustle.py`
（`AC.make_agent(AC.LUCARIO_DECK)` — 我々の元デッキ系譜(lucario_v2)と同系統のジェネリック相手）

## 構造的事実
- 我々自身の出発点（lucario_v2）に近い、ex主体の標準的な攻撃デッキ。相性は元来良好。
- 応手ガード（相手の反撃を読む）が最も安定して効く相手 = 相手の攻撃パターンが単純で読みやすいため。

## 我々の勝率履歴
| 版/施策 | 対ex_lucario勝率 | 出典 |
|---|---:|---|
| v011 revenge-window | 0.755 | submissions.csv |
| v012 deck-ratio | 0.71→0.77 | submissions.csv |
| v013 応手ガード（発表時） | **0.77→0.86**（+0.09, ~2.6SE） | submissions.csv |
| v013 再測定（2構成, exp029追記） | 0.770/0.775（**0.86は再現せず**） | exp029 SESSION_NOTES 2026-07-04追記 |
| v014 turn-beam | 0.770 | submissions.csv |
| exp038 depth=2（n=40, バグ全修正後） | 0.500（悪化） | exp038 SESSION_NOTES |
| exp039 archetype模倣ガード（n=100, 1回目） | 0.83（v014比 +0.06, 明確な改善） | exp039 SESSION_NOTES |
| exp039 + archaludonゲート（n=100, 2回目/独立再測定） | **0.78**（v014比 +0.01, ほぼフラット。**+0.06は再現せず**） | exp039 SESSION_NOTES 2026-07-05 |

## 適用済みルール
- なし専用ゲートはない。応手ガード（v013由来のカテゴリカルdoom-veto）がここで最も安定して効く。

## 未解決の論点
- **重要な教訓（2回繰り返し確認済み）**: v013発表時の「0.86」は2回の独立再測定で再現せず（0.770/0.775）、さらに
  exp039の「0.83」も2回目の独立測定では0.78（v014比+0.01）に収束した。**この相手はn=100でも単発の高い数字を
  信用してはいけない** — 再現性を1回確認するまでは「改善」と呼ばない、という教訓がこのマッチアップだけで
  3回連続で成立している。今後このマッチアップで良い数字が出た場合は、必ず独立な2回目のn=100測定を行うこと。
