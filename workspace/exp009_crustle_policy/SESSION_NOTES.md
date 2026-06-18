# exp009_crustle_policy — SESSION NOTES

## 仮説
v004(汎用 lucario_v2 方策で Crustle デッキ)= LB 627 の失敗原因は「汎用方策が制御デッキを操縦できない」。
専用の Crustle 制御方策を書けば、模倣(Crustle control)を機能させ、メタの両極(模倣＋カウンター)を取れる。

## 実装 (`crustle_policy.py`)
- コンテキスト別の優先度スコアリング（手ルール, クラッシュ安全, 探索なしで高速 0.005s/手）:
  - MAIN: ABILITY > EVOLVE(Dwebble→Crustle) > ATTACH(エネ) > PLAY(Poffin/回復/HeroCape/Lillie) > ATTACK(Crustle 120) > RETREAT > END。
  - 回復(Jumbo80/Cook70)は active が20以上削れている時のみ。Lillie/Waitress はデッキ残≤7で抑制(デッキアウト回避)。
  - CARD選択: 探索/手札化/進化は Dwebble/Crustle を最優先、discard は Pokémon 線を温存。回復対象は Crustle。
  - YES_NO: IS_FIRST/ACTIVATE は Yes、MULLIGAN は No 寄り。
- カード効果は実データで確認: Dwebble Ascension(自己進化), Crustle Superb Scissors 120, Hero's Cape +100HP,
  Grow Grass +20HP, Jumbo/Cook 回復, Buddy Poffin で基本展開, Lillie ドロー。

## 評価 (n=16)
| control vs | 勝率 |
|---|---|
| ex_Lucario | 0.69 |
| dragapult | 1.00 |
| v003_counter | 0.44 |
| v004_genericCrustle(ミラー) | 0.19 |

- 1ゲーム精査: **セットアップ成功時は圧勝**（進化5・攻撃15・サイド6完取・デッキアウトなし）。方策は健全に機能。
- ただし aggregate は汎用 v004 と ex デッキで同等（0.69/1.00）。伸び悩みは**序盤ブリック→場ポケ不在負け**と
  **ミラーの泥仕合(デッキアウト競争)**が主因（reason=3 多発）。
- ex Lucario が 1.00 でない理由: 相手デッキの Hariyama(非ex)が Crustle を貫通できるため。

## 提出
- **v005** 提出（ref 後述）。弱い v004(627) を最新2枠から上書き。専用制御の実力をラダーで実測する。
  最新2 = {v005, v003=950.7}。

## 学び / 次
- 制御デッキの手ルール操縦は「セットアップ成功時は強いが、事故率とミラーが課題」。
- v005 の LB 次第:
  - 627 を明確に上回れば「専用方策で模倣が機能」＝メタ両極確保。さらに事故率低減(マリガン/序盤展開)を詰める。
  - 改善しなければ、模倣路線は投資対効果が低い → カウンター(v003=950.7)を主軸に。
- v003(カウンター)が現状の主力で確実。
