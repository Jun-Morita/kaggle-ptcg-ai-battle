# exp011_meta_watch — SESSION NOTES

週次サイクルの「リプレイDLでメタ確認」を関数化した実験ディレクトリ。

## ツール
- `analyze.py <submission_id> [tag]`: 自分の最新提出のラダー対戦リプレイを全DL
  (`references/raw/replays/<tag>/`, gitignored) → 相手デッキ＋勝敗を抽出し、
  アーキタイプ別 W-L を集計。`results/meta_<tag>.json`(gitignored) に保存。
- `matchup.py [n]`: 候補エージェント同士のローカル対戦（v003 / lucario_v2 / crustle_v005 / crustle_v004）。

## 2026-06-20 メタ確認（sub 53846234 = 最新v003, 46試合）
**メタが一周した。Crustle 一色 → ex ビート(Lucario-ex)復権。**

| 相手アーキタイプ | 我々(v003)の W-L | 勝率 | 占有 |
|---|---|---|---|
| lucario_ex | 8-18 | **0.31** | 26 (57%) |
| crustle_control | 8-1 | 0.89 | 9 (20%) |
| mixed_ex | 5-1 | 0.83 | 6 (13%) |
| non_ex_attackers | 3-1 | 0.75 | 4 (9%) |
| dragapult | 1-0 | 1.0 | 1 (2%) |

- v003 低下(1123→975)の正体 = **自身が Lucario-ex デッキでミラーに負け越し**。
  anti-Crustle patch は効くが、Crustle はもう 20% しかいない。
- LB top も再編: Praxel(~1388)消滅 → hiroingk 1299.8 / Debauchery Tea Party 1269.6 /
  Stagapult 1268.8 / Kadoraba 1267.4。
- field の非ex = Hop's Trevenant/Phantump+Snorlax、Abra-Kadabra-Alakazam。

## カウンター検証（matchup.py, n=30/24, 先後入替）
| マッチアップ | 勝率 |
|---|---|
| crustle_v004(汎用) vs lucario_v2 | **0.867** |
| crustle_v005(専用) vs lucario_v2 | 0.667 |
| v003 vs lucario_v2 | 0.467 |
| crustle_v004 vs crustle_v005 (ミラー) | **0.79** |
| crustle_v00X vs dragapult(ex) | 1.000 |
| crustle_v00X vs iono(妨害) | **0.0-0.04（弱点）** |

- **意外**: 汎用 lucario_v2 方策で Crustle を操縦する v004 が、専用 v005 より全面的に強い。
- Crustle 壁は全 ex デッキを食うが、iono/非ex妨害に全敗 = 三すくみの残り一角。
- 期待 field 勝率: **Crustle ≈0.65 ≫ v003 ≈0.52(=現975)**。

## アクション
- v004 Crustle anti-ex 壁を再提出（2026-06-20, build_v004/submission.tar.gz, 0.75 vs lucario 実artifactスモーク済）。
- eligible = **{v004 Crustle カウンター, v003 過去最良}** = 三すくみヘッジ
  （ex を v004 で食い、Crustle 復活は v003 で受ける）。
- 次回週次: 新 sub の収束後に再度 analyze.py でメタ再確認。大変化なければ静観。
