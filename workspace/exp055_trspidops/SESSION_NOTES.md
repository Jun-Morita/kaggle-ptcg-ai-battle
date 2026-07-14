# exp055 — TR Spidops再現スパイク（床パイロット） → NO-GO（撤退）

## 仮説（1実験1仮説）
TR Spidopsの対Safeguardメタ優位（実測: 9位Marshall Maximizerがv023-LOに3-0、#7 Budew壁に3-0）は
**デッキ構造由来**（非ex攻撃がSafeguard/Neutralization Zoneを素通り）なので、床パイロット
（汎用政策）でも発現するはず。

**ゲート**: 対純壁≥0.6 かつ 対LO(koff)≥0.6、対alakazam/archaludonで壊滅しない(≥0.45)。

## 材料
- `tr_deck.json`: Marshall Maximizerの実60枚（v023戦リプレイから抽出、2試合で同一リスト）。
  Tarountula×4→Spidops×4(130HP)、Articuno×2、Mimikyu×3、**Mewtwo ex×2(280HP)**、
  TRエンジン（Transceiver×4/Ariana×4/Proton×4/Giovanni×3/Archer×1）、TR Factory×3、
  TR Energy×4＋草9、Bug Catching Set×3、Cape/Bangle。※完全非exではない（Mewtwo ex入り）

## 結果（floor_test.py, n=100/セル, CRN共通シード, err=0）

| 対戦相手 | 床パイロット | ゲート | 実物(Marshall)の実績 |
|---|---:|---|---|
| 純壁 | **0.720** | ✓(≥0.6) | 3-0 |
| **LO(v023-koff)** | **0.280** | **✗(≥0.6)** | 3-0 |
| alakazam | 0.760 | ✓ | — |
| **archaludon** | **0.050** | **✗✗(≥0.45)** | — |

（generic(AC)とrevenge(RVP)は完全同一——RVPはフラグ未設定時AC系と同一挙動＝実質1パイロット）

## 判定: NO-GO（2/4ゲート不通過、撤退）
- 対壁0.72は構造エッジの部分的発現だが、**対LO 0.28**（実物は3-0）と**対archaludon 0.05**
  （現高度シェア31-45%）が致命的。実物との差は60枚同一なので**純粋にパイロット差**。
- これはexp013 Debauchery模倣（TRエンジンbrick、ex 0.167→努力しても0.53）と同型の
  deck⊗pilot不可分の再演。TRサポーターエンジン（Transceiver→Ariana/Proton/Giovanni選択）は
  我々の汎用パイロットが最も苦手とする機構であることが3度目の確認。
- 専用パイロット開発は「模倣の深追い」（過去に一度も勝ちを生んでいない）に該当し、
  残り1ヶ月のリソース配分として不適。**LO路線（v023/v024収束＋リロール）継続が正**。

## 得たもの
- TR Spidopsのローカル代理（tr_deck + 床パイロット）を帯域プールに追加可能になった
  （対TR勝率の測定手段。ただし床パイロットは実物より大幅に弱い点に注意——
  「対床0.72の壁」が実物には0-3で負ける）。
- 非exアグロトリガー発動時の選択肢は「TR再現」ではなく「v020 Archaludon投入」
  （床テストでarchaludonがTRを0.95で轢くことが判明＝**TRメタの正解は既に手元にある**）。
