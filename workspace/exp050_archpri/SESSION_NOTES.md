# exp050 — v020(Archaludon)パイロットへのSEARCH_PRIレシピ横展開 → 両施策NO-GO

## 背景・仮説
disc721338で「Boss's Orders/Ultra Ball捨て札は14位でも未解決」と判明。v020のデッキは
Ultra Ball×4/Boss's Orders×4を積むため、実証済みのSEARCH_PRIレシピ（トップ勢リプレイ
からの状態条件付き学習差し替え、exp043/047で2連続GO）をv020パイロットに適用すれば
差を作れるのではないか。

## データ収集
mixed_ex4上位3人のリプレイを取得・プール:
- ShumpeiNomura(LB 1083.6): deck_54588173(65) + top_arch_54253844(311)
- Canon(1048.5): top_arch_54377442(98)
- Takaaki Matsuda(903.3): top_arch_54484706(98)

抽出(exp047のextract_selects_ctx.py流用): **DISCARD 818決定/469試合、TO_HAND 3,083/560**。
学習(train_pri.py無改造): DISCARD val 0.569-0.608 vs 静的0.549（弱い優位、val n=51）、
TO_HAND 0.685-0.774 vs 静的0.518。

## ギャップマップ（policy_diff_fixed.py、現パイロット vs Nomura、150試合）
| context | 一致率 | 判断 |
|---|---:|---|
| DISCARD | **0.27** | 最大の非MAINギャップ→学習差し替え試行 |
| IS_FIRST | **0.00**(77/77) | パイロット後攻固定 vs Nomura先攻固定→反転試行 |
| TO_HAND | 0.76 | 学習モデル(0.685-0.774)と同水準→見送り |
| MAIN | 0.57(sem) | 最大だがシーケンシング本体、対象外 |

## 結果: 両施策ともpaired(ミラー・別ビルド・swap_sides)でNO-GO

1. **IS_FIRST反転**(choose second→go first): ミラーn=200 **0.420 (84-116, z≈-2.3)明確悪化**。
   フィールドはフラット(crustle 0.790/ex 0.695/drag 0.660 ≒ 基準0.805/0.645-0.660/0.655)。
   ミラー=メタ16%なので却下。後攻選択はこのエンジンでは正しい模様。
2. **学習DISCARD差し替え**(SEARCH_PRI型、リテラル展開、発火計測付き): 発火は正常
   (30試合37回、fallback 0、エラー0)だが ミラーn=400 **0.470 (188-212, z≈-1.2)**。
   正の兆候なし＋学習側の優位が元々弱いため、n=1000に積まずNO-GO。

## 教訓
- **「トップ勢一致≠強さ」の3例目・4例目**（exp042 bench-disc、exp048 Starmieに続く）。
- exp047のDISCARD成功は「基底ポリシーにスコアリング分岐が皆無」という構造的空白が
  前提だった。**既に調律済みのロジックを持つパイロットに対しては、一致率の低さは
  「未調律」ではなく「別の（有効な）方針」を意味しうる**。公開Archaludonパイロットの
  後攻固定・独自捨て札ロジックは、Nomuraと違っても勝率的には既に最適圏。
- disc721338のChrismaghuhn実装教訓（発火計測）は採用して機能した。再利用価値あり。

## 資産
- `extract_selects_ctx.py`によるマルチプレイヤー・プール抽出パターン(818+3083決定)。
- `arch_pilot_wrapper.py`(公開パイロットをpolicy_diff_fixedに接続)。
- `build_discard.py`(公開パイロットのchoose_optionsへの学習オーバーライド注入テンプレ、
  発火カウンタ付き)。TO_HANDや他文脈で再試行する場合はここから。

## 判定
exp050クローズ。v020は素のまま維持（現eligible = {v019, v020}変更なし）。
次はラダー実測値（v020の収束・ミラー実戦値）の監視を優先。
