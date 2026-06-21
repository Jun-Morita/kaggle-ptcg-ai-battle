# exp013_router — SESSION NOTES

仮説: 「デッキで使い分ける」deck-dispatch 方策を作り、#1 Debauchery（TR エンジン非ex）を含む複数デッキを
1つの方策で操縦する。きっかけ: Debauchery の60枚を v007 方策で操縦すると ex 0.167 でブリック（強さの源泉の
Team Rocket tutor エンジン＋Cramorant が未操縦）。

## 実装（`router_policy.py` PATCH_SRC）
- `_DECK_NONEX = (Trevenant or Phantump in my_deck)` でデッキ検出 → 非ex時のみ非exロジックを適用（dispatch）。
- `_base_attack` を**カードで分岐**（Lucario カード=元ロジック / 非exカード=非exモデル）。
- 非ex攻撃モデルに **Cramorant**(1エネ120, 相手サイド3-4限定)・**Postwick +30**(スタジアム, Hop's限定)・
  Extra Helpings +30(Snorlaxベンチ)・Choice Band +30/コスト-1 を追加。`_plan_attack` は弱点タイプ修正(v007流)。
- **search-target priority**（`_score_to_hand`）: tutor(Petrel/Hilda/Transceiver/Secret Box)が
  Phantump→エネ→Trevenant→Cramorant→Choice Band を取るよう優先度付け。←ブリック解消の本命。

## 結果（先後入替, n=各記載）
### Debauchery デッキ + dispatch（v007 では ex 0.167 だった）
- vs ex **0.533**（0.167→大幅改善, ブリック解消）/ Crustle 0.600 / dragapult 0.167 / 対v007 0.525。
- ただし Debauchery 実物(0.78)・我々charmq+v007(0.71) には未到達。TR/Cramorant の精緻操縦が残課題。
  → **#1 デッキの本来の強さは未制覇**（deck⊗pilot は深い）。

### ★本命の収穫: charmq デッキ + dispatch が v007 を上回る
| charmq+dispatch | 勝率 | v007 比 |
|---|---|---|
| vs charmq+v007（直接対決, 160g合算） | **~0.56** (n60:0.60, n100:0.54) | +改善 |
| vs lucario_v2 (ex) | **0.800** | 0.71→0.80 |
| vs Crustle | **0.767** | 0.625→0.767（v007退行を回復） |
| vs dragapult | 0.167 | 同 |
- サーチで正しいカードを取る＝**消費安定性向上**が全マッチアップを底上げ。ミラー上限と Crustle 退行を同時突破。
- **v008 = charmq デッキ + dispatch 方策**（`build_v008/submission.tar.gz`, 実artifactスモーク0エラー）。

## 結論 / 次
- deck-dispatch アーキタクチャは成功。**副産物の search-priority が我々の主力 charmq を強化** → v008。
- Debauchery デッキ自体の制覇は partial（プレイアブル化のみ）。本格模倣は TR エンジン操縦の更なる作り込みが必要。
- 提出案: v008 を出して eligible **{v008, v007}**（負債 v006 を排除, v008 主力）。dragapult 弱点は据置(希少)。
