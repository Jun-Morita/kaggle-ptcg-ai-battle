# exp031 — exact revenge window（エンジンソース準拠）

## 仮説
エンジンソース（SatisfyCondition.h: koAttackDamageHop）より、v011 の window proxy
「相手がサイドを取った」は非Hop's（Dudunsparce）KO で偽陽性 → RB=50 が最良だったのは
偽陽性ヘッジ。窓を正確化（サイド取得 AND 我々トラッシュの Hop's 増加）すれば実値 RB=100 が安全になるはず。

## 結果（n=200 vs exp027 field, 全て 0err）
| matchup | v012基準(proxy50) | exact RB=100 | exact RB=50 |
|---|---|---|---|
| ex_lucario | 0.77 | 0.765 | 0.750 |
| dragapult | 0.155 | 0.145 | 0.165 |
| archaludon | 0.175 | 0.175 | 0.120 |
| mirror_chq | 0.585 | 0.570 | 0.540 |
| crustle | 0.765 | **0.850 (+0.085, ~2.4SE)** | 0.795 |

- **exact RB=100 > exact RB=50**（5マッチ中4勝）＝「窓の正確化で強い値が安全になる」を確認。
- 対基準では **crustle のみ明確な改善**、他は同水準（ミラー −0.015 はノイズ内）。
- 機構: crustle 戦は Trevenant が壁を割る長期戦＝revenge の 130 打点が Crustle(HP110+Cape)圏に
  刺さる局面が多い。正確な窓で 130 を確実に計画に載せられる。

## 判定
単独では v012 比 +crustle のみだが退行なし・仕様準拠化として価値あり。
**guard(exp029) と統合した v014 候補（GUARD_BASE=exact RB=100 + K=4 guard）を n=200 で評価中**
→ guard の ex_lucario +0.09 と exact の crustle +0.085 が両立するかが焦点。

## レポート材料
「観測から機構を推定（RB=50 の頑健性）→ ソース公開で偽陽性の機構を特定 → 修正で実値が解禁」
は Strategy レポートの再現性/誠実性の軸に良い実話。

## 統合評価（guard K=4 ＋ exact RB=100 = v014 候補, n=200）→ 見送り

| matchup | 基準 | v013(guard+proxy50) | exact100単独 | v014候補(guard+exact100) |
|---|---|---|---|---|
| ex_lucario | 0.77 | **0.860** | 0.765 | 0.770 |
| dragapult | 0.155 | 0.205 | 0.145 | 0.185 |
| archaludon | 0.175 | 0.165 | 0.175 | 0.175 |
| mirror_chq | 0.585 | 0.555 | 0.570 | 0.530 |
| crustle | 0.765 | 0.795 | **0.850** | 0.790 |
| 合計 | 2.45 | **2.58** | 2.505 | 2.45 |

- **exact の crustle +0.085 は guard との統合で消失**（0.850→0.790）。ex も v013 の 0.860 を再現せず。
- 解釈: (a) proxy 窓の「偽陽性」は Dudunsparce KO 後にも Trevenant 計画を攻撃的にする
  **偶発的に有益な副作用**を持っていた可能性。(b) この帯の ±0.05-0.09 は n=200(SE≈0.035) では
  ノイズ境界＝v013 の ex 0.860 自体が上振れの可能性も残る（disc 712621 の教訓と整合）。
- **判定: v013（出荷済）維持、v014 見送り。** 仕様準拠 exact 窓は「単独 crustle 特化」としてアーカイブ
  （将来 crustle シェア急騰時の選択肢）。
- レポート材料: 「ソースで偽陽性の機構を特定 → 修正はローカルで中立〜微減 → 近似の偶発的頑健性」は
  ヒューリスティック系の面白い honest finding。
