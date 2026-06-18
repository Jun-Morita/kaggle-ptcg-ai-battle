# exp007_anti_crustle — SESSION NOTES

## 仮説
ラダー支配メタ = Crustle anti-ex control。我々の全-ex Lucario は構造的に勝てない（実戦 0/4）。
非ex attacker で Crustle(Safeguard=ex のみ無効)を貫通すれば勝てるはず。デッキ/方策で対策する。

## 敵の分析（リプレイ由来, `crustle_deck.json`）
- Crustle control 60枚: Dwebble344×4, Crustle345×4, 草エネ19, Mist/Spiky/GrowGrass 特殊エネ各4,
  Buddy-Buddy Poffin×4, Jumbo Ice Cream×4, Cook×4, Lillie×4, Waitress×4, Hero's Cape×1。
- **Crustle(345)**: HP150, Stage1(←Dwebble), 特性「Mysterious Rock Inn」= 相手ポケモンex の攻撃ダメージを全無効。
  攻撃 Superb Scissors 120（相手アクティブの効果に影響されない）。回復(Jumbo/Cook/Waitress)＋ドロー(Lillie)で粘る。
- **弱点 = 非ex**: Safeguard は ex のみ。**Hariyama(674,非ex) Wild Press 210 → Crustle(150)を一撃KO**（自傷70）。
  我々の Lucario デッキに Hariyama×2/Makuhita×2 が既にある。Solrock70/Lunatone50 も非ex。
  Mega Lucario(678)は megaEx ＝ Crustle に無効。

## 再現（ローカルハーネス）
- Crustle 相手 = lucario_v2 方策 + crustle_deck（汎用方策で Crustle を運用）。
- **Lucario(ours) vs Crustle = 0.20（4-16, n=20）** → ラダー(~0/4)を再現。改善を測れる。

## 試行
### デッキ変種（Hariyama 寄せ: Makuhita/Hariyama 2→3, Lucario 4→3, Riolu 3→2）
| デッキ | vs crustle | vs mirror | vs dragapult |
|---|---|---|---|
| BASE | 0.19 | 0.50 | 0.56 |
| HARIYAMA+ | 0.25 | 0.44 | 0.50 |
- **デッキだけでは改善せず**（0.19→0.25, 誤差）、他マッチアップは微減。
- **確定: 問題は方策**。lucario_v2 は ex の Lucario を Crustle に撃ち続け、Hariyama 線に切り替えない。

### belief-PIMC（相手=Crustle と信じて探索）vs Crustle
- **0.50 (5-5)** ＝ルールベース 0.20 から**2倍超に改善**。探索は ex 攻撃の無効を見て部分的に良い線を発見。
- ただし: 五分でメタ撃破には不足 / **36秒/手と激遅** / Crustle belief 前提（ラダーは推定要）。
  rollout 方策が Lucario 寄りで Hariyama 線を突き切れていない。
- 示唆: 探索は「相手モデルさえ合えば自動でメタ適応する」ことを実証（Strategy レポート強化）。
  だが**確実・高速・支配的にするには方策レベルの非ex ルーティングが要る**。

### 方策オーバーライド（外科的1点修正）★成功
- `patch_policy.py`: lucario_v2 の `_plan_attack` の damage 計算後に
  「攻撃側が ex/megaEx かつ相手が ex-免疫(Safeguard)なら damage=0」を挿入。
  → 既存の attack-planning が「Lucario で Crustle を殴っても0」と理解し、**自動で Hariyama(210)線に切替**。
- **結果 (n=20)**:
  | | vs crustle | vs mirror | vs dragapult |
  |---|---|---|---|
  | BASE(原) | 0.10 | 0.65 | 0.60 |
  | **PATCHED** | **0.60** | 0.60 | 0.70 |
- **Crustle 0.10→0.60 に逆転、他は不変〜改善**。確実・高速(探索不要)・支配的。belief-PIMC(0.50/36s)より優秀。
- これを v003 として提出（v001=915 は Crustle 全敗 → 大幅 LB 改善見込み）。

## 次アクションの候補
- (A) 方策オーバーライド: 相手アクティブが ex-immune(Crustle/Safeguard) のとき、ex Pokémon での攻撃を抑制し
  非ex attacker(Hariyama)の準備・攻撃を優先。最も確実だが実装が要る。
- (B) belief-PIMC が自動解決するなら、メタ対応は探索で吸収（独創性高）。
- (C) 専用アンチコントロールデッキ（強い非ex attacker 主体）。
- 評価プールに Crustle を常設し、対メタ勝率を主指標にする。
