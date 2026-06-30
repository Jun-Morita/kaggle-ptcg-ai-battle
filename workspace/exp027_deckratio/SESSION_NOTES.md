# exp027 — デッキ比率最適化（stagnation breaker）→ v012 提出

## 動機
v011 が ~825 で停滞。診断: pilot は天井、mixed_ex は ex のロングテール（単一ターゲット無し）。
**未試行の梃子＝デッキ比率**（これまで pilot(v007-v011) と 1枚差し替え(NZ/Crustle) しか変えていない）。

## 発見: charmq は attacker-light
charmq の Pokémon: Phantump×4 / **Hop's Trevenant×2(主力140HP Revenge)** / Snorlax×2 / **Cramorant 0** + Dunsparce/Dudunsparce(draw)。
engine ~33枚と過剰、attacker 薄。**top 非ex(Yushin/Debauchery)は Trevenant×4＋Cramorant×3**。
我々の policy は Cramorant(311) ロジックを持つのにデッキに不採用＝dormant。
→ 「4 Phantump あるのに進化先 Trevenant 2 ＝ stuck on Phantump」（mirror_analysis の負け筋）。

## sweep（v011 revenge で操縦, ex-heavy field, n=80→200）
| 変種 | ex_luc | drag | arch | mirror | crustle |
|---|---|---|---|---|---|
| charmq(base) | 0.71 | 0.13 | 0.13 | 0.465 | 0.71 |
| v_cram(+3 Cram) | 0.73 | 0.15 | 0.09 | 0.49 | **0.66↓** |
| **v_trev(Trev 2→4, -2 Brock)** | **0.77** | 0.155 | 0.175 | **0.585** | 0.765 |
| v_both(+2Cram+2Trev) | 0.66↓ | 0.09 | 0.025↓ | 0.475 | 0.75 |

- **v_trev が全マッチ改善・退行ゼロ（n=200, SE≈0.035）**: ex_lucario +0.06(大票田), **mirror +0.12(~3.4SE)**, crustle +0.055, archaludon +0.045, dragapult +0.03。
- v_cram/v_both は Crustle 退行（Cramorant は opp 3-4 prizes 限定＋engine 希釈）。Trevenant 増量が正解。
- 機構: 主力 Trevenant を厚くし「stuck on Phantump」を解消＝あらゆる攻撃マッチで底上げ。**top 構築(Trev×4)に一致**。

## 提出 v012（ユーザー承認済 2026-06-30, sub 54213076）
- deck = charmq + Trevenant 2→4（-2 Brock's Scouting）, policy = v011 revenge(RB=50)。
- built smoke 0err crash-safe（deck.csv: Trev 4 / Phantump 4 / Brock 0 / 60）。
- **eligible = {v012, v011}**（v006 662 押し出し）。LB は best-of-2＝score=max。
- **転移確度が pilot tweak より高い理由**: deck-composition の real edge（top 構築一致）、broad gains、mirror +0.12 は大。CV/LB 乖離の前科ありゆえラダーが最終判定。

## 資産
- `v_cram/v_trev/v_both.json`（変種）/ `eval_ratio.py`（DECK 指定で ex-heavy field 評価）/ `build_v012/`。
- 次の比率最適化候補: Trevenant×4 を保ちつつ Cramorant を別カット枠で少量試す / Snorlax 比率 / draw を更に絞る、等（v_trev を新 baseline に）。
