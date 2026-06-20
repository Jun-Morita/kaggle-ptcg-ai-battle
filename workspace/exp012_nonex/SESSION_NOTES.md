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
