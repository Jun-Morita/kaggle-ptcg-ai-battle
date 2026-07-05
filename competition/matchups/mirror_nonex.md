# ミラー（Hop's Trevenant 非exミラー, charmq系統）

fine_classify キー: `"Hop (non-ex Trevenant)"` — 我々自身のデッキアーキタイプ。field battery では `gust_policy.make_agent(CH)`
（charmqデッキを汎用方策で操縦した相手）との対戦として計測。

## 構造的事実
- 同一デッキ同士のため、**操縦（piloting）の質そのものが勝敗を分ける**唯一の変数。exp022で「操縦が#1レバー」と確定した根拠マッチアップ。
- 主な転移した機構修正:
  - **gust修正**（exp022, v010）: #3 Mogja精読で「Boss's Ordersでベンチをgust+KOしてサイドを取る」漏れを発見・修正 → ミラー0.685(=Mogjaの0.68に一致)。
  - **revenge-window修正**（exp023, v011）: Hop's Trevenant「Horrifying Revenge」の+100機構をpilotが見落とし → window検出+50 → ミラー0.45→0.505。
  - **deck-ratio修正**（exp027, v012）: Trevenant 2→4（Phantumpに詰まる問題を解消）→ ミラー0.465→0.585（+0.12、最大の単発改善）。

## 我々の勝率履歴
| 版/施策 | 対ミラー(charmq)勝率 | 出典 |
|---|---:|---|
| v006 vs v006（初期apex） | 0.685(vs v006, ==Mogja) | exp022 SESSION_NOTES |
| v011 revenge-window | 0.45→0.505 | submissions.csv |
| v012 deck-ratio | 0.465→**0.585**(+0.12) | submissions.csv |
| v013 応手ガード | 0.555（-0.03, ノイズ域） | submissions.csv |
| v014 turn-beam | 0.580 | submissions.csv |
| exp038 depth=2（n=40, バグ全修正後） | 0.250（悪化） | exp038 SESSION_NOTES |
| exp039 archetype模倣ガード（n=100） | 0.600（v014比 +0.02） | exp039 SESSION_NOTES |

## 適用済みルール
- なし専用ゲートはない。deck-ratio修正（v012）が最大の恒久的改善。

## 未解決の論点
- ミラーは「対称なので五分が理論上限に近い」性質があり、大きな伸びしろは考えにくい。deck-ratio級の実機構発見（gust/revenge-windowと同じ「達人精読で漏れを発見」パターン）が今後も最有力レバー。
