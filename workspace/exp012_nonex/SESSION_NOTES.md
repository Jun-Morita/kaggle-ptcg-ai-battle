# exp012_nonex — SESSION NOTES

仮説: トップ解析(exp011)で判明した **apex アーキタイプ = 非ex アタッカー**（charmq LB#4）を複製し、
三すくみの頂点を取る。非ex は ①単サイドで ex(2-3サイド)にレース勝ち ②Crustle の ex 限定 Safeguard を
貫通、で ex ビートと壁の両方に勝つ。

## デッキ（charmq の正確な60枚, リプレイ実データから抽出, `charmq_deck.json`）
Hop's Phantump×4→Hop's Trevenant×2(HP140) / Hop's Snorlax×2(HP150, basic) /
Dunsparce×4→Dudunsparce×3(ドロー機関) / Hop's Choice Band×4(打点道具) /
Buddy-Buddy Poffin×4・Pokégear×4・Poké Pad×4・Hop's Bag×3・Lillie's Determination×4(consistency) /
Boss's Orders×2(呼出)・Colress's Tenacity×2・Brock's Scouting×2 /
Night Stretcher×3・Postwick×4(スタジアム) / Mist Energy×4・Telepath Psychic Energy×4・Legacy Energy×1。**全非ex**。

## 検証（test_nonex.py, 汎用 lucario_v2 方策で操縦, n=30, 先後入替）
| 相手 | 勝率 | charmq実測 |
|---|---|---|
| lucario_v2 (ex) | **0.667** | 0.69 ✓ |
| Crustle (v004) | **0.833** | 0.70 ✓✓ |
| v003 (我々のex) | **0.600** | — |
| dragapult | 0.100 | 弱点（スプレッドで低HP多数を狩られる） |

- **汎用方策でも apex 性能を再現**（0エラー）。v004 と同じく汎用方策で複雑デッキを操縦できた。
- v004 Crustle の上位互換: ex を同等(0.67)に食い、**Crustle を 0.83 で圧倒**（v004 は Crustle ミラー0.60止まり）。
- 唯一の弱点 = dragapult(スプレッド)。field の~2%と希少。

## 提出（2026-06-20, v006）
- `build_v006.py` → `build_v006/submission.tar.gz`（deck + 汎用方策 + crash-safety, スモーク0エラー）。
- eligible = **{v006 非ex apex, v004 Crustle}**（v003 押し出し）。
  v006=apex(ex+Crustle を食う) ／ v004=v006 の弱点 dragapult を 1.0 でカバーするヘッジ。
- 三すくみの全角を実質カバー。収束を待って analyze.py で実戦績を確認予定。

## 次の改善余地
- dragapult/スプレッド対策（HP高めの非ex、または手数で押し切る）。
- 非exミラー（charmq 系同士）の操縦改善＝専用方策の余地。
- 上位帯の field 再解析（非exが飽和したら別の counter が必要）。

## 専用非ex方策（mirror 強化, nonex_policy.py / v007）2026-06-20
**診断**: 汎用 lucario_v2 は非exデッキで `_base_attack` が全 None → **plan を作らず**、Boss's Orders
(plan.target≥1 で発動)・リトリート/switch(plan.attacker≥1)・対象選択・エネ配分・KO認識が**全て死んでいた**。
**パッチ（v003流, rewrite せず的を絞る）**: `_base_attack` に非ex攻撃を付与（Extra Helpings +30＝Snorlaxベンチ,
Hop's Choice Band +30/コスト-1）＋ `_plan_attack` を弱点タイプ正しく上書き（Trevenant/Phantump=Psychic, 他=Colorless）。
下流（Boss's Orders/リトリート/対象/エネ）は plan に配線済みなので一斉に作動。

**結果（test_smart.py, n=40, 先後入替）**:
| マッチアップ | smart | generic(v006) |
|---|---|---|
| **mirror (smart vs generic, 同一デッキ)** | **0.775**(31-9) | 0.50(対称) |
| vs lucario_v2 (ex) | **0.725** | 0.667 |
| vs Crustle | 0.625 ↓ | 0.833 |
| vs dragapult | 0.100 | 0.100 |

- **ミラーで 0.775 と圧勝**＝同一デッキでの操縦差（狙い通り）。ex も改善。
- Crustle に退行（壁相手に Boss's Orders 等を使い過ぎる副作用と推測）。dragapult 弱点は不変。
- ビルド `build_v007.py`（PATCH_SRC を main.py に焼込, deck=charmq）。実artifactスモーク: 対generic 0.625, 0エラー。
- メタは非exに収束中（Crustle 減）→ ミラー強化は未来志向で正解。提出案 eligible {v007 smart, v006 generic}
  （v007=ミラー+ex, v006=Crustle カバー, 両非ex）。

## v008 ミラー強化の試み = 誠実なネガティブ（2026-06-20）
v007（ミラー実戦0.56）から更にミラーを伸ばそうと2レバーを試作（`nonex_policy_v8.py`）。**いずれも不発**。
1. **エンジン剥がし**（相手 Snorlax[Extra Helpings]/Dudunsparce[ドロー] を target_score で優先）:
   v8 vs v7 ミラー **0.500**(n=40), 対generic **0.40**（むしろ悪化）。150HP Snorlax を倒し切れず Boss's Orders
   で釣る＝テンポ損（v007 の Crustle 過釣りと同じ失敗）。
2. **開幕 active 選択**（Phantump で殴り線、Snorlax はベンチ温存）: v8 vs v7 = 0.56(n=50) と一瞬期待もったが
   **n=100 で 0.490**＝ノイズ。退行なし(ex 0.708/Crustle 0.917)。
- **結論**: 同等品質方策同士の非exミラーは対称で coin-flip。**v007 はヒューリスティック上限**。上位の高ミラー率は
  相手が弱い非ex使いだった分が大。これ以上のミラー改善は search/学習が要るが RL は3重ネガティブ（[[rl-status]]）。
- v008 は**提出しない**（非改善）。代わりに eligible の負債 v006(ミラー0.31) を外し v007 を主力に。
