# Crustle（壁・ex耐性）

fine_classify キー: `"Crustle"` / 自前実装: `workspace/exp007_anti_crustle/anti_crustle.py`（`CRUSTLE_DECK`, 実メタ複製）

## 構造的事実
- Crustle（Dwebble系）は **Safeguard**（ex/megaEx攻撃を無効化）を持つ壁。純ex構成は0ダメージで詰む（exp007発見時の教訓）。
- 我々のデッキ（Hop's Trevenant非ex中心）は**元々Safeguardを貫通する**（非ex攻撃のため）。ex主体だった旧構成（v001時代）とは事情が異なる。
- v011以降の revenge-window/deck-ratio/turn-beam の改善が軒並みここに乗る＝**我々の主戦場・改善が最も複利で効くマッチアップ**（v014のturn-beamが+0.14と最大の伸びを見せた相手）。

## 我々の勝率履歴
| 版/施策 | 対Crustle勝率 | 出典 |
|---|---:|---|
| v001（ex主体, 貫通なし） | 0.10 | exp007 SESSION_NOTES |
| v006（非ex apex複製） | 0.833 | submissions.csv |
| v011 revenge-window | 0.730→0.780 | submissions.csv |
| v012 deck-ratio | 0.765 | submissions.csv |
| v013 応手ガード | 0.795 | submissions.csv |
| v014 turn-beam | **0.905**（+0.14, 現行最良） | submissions.csv |
| exp038 depth=2（バグ全修正後, n=40） | 0.675（v014比劣化） | exp038 SESSION_NOTES |
| exp039 archetype模倣ガード（n=100） | **0.91**（v014同等以上） | exp039 SESSION_NOTES |

## 適用済みルール
- なし専用ゲートはないが、turn-beam（v014）の系列化がここで最も効く。exp039も同水準を維持。

## 未解決の論点
- 現状ほぼ天井（0.90+）。これ以上の改善余地は小さいと見て良い。他マッチアップへのリソース配分を優先。
