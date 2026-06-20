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

## 2026-06-20 トップランカー解析（top_meta.py で上位プレイヤーの試合を辿る）
上位2名の自デッキ＋対戦相手アーキタイプを実データ解析。**完全な三すくみが頂点で回っている。**

### charmq（LB #4, 1259）= 非ex アタッカー（apex）
- デッキ: Hop's Phantump×4→**Hop's Trevenant**×2(HP140), Hop's Snorlax×2(HP150),
  Dunsparce×4→**Dudunsparce**×3(ドロー機関), Hop's Choice Band×4(打点UP道具),
  Boss's Orders×2(呼出), 特殊エネ(Telepath/Mist/Legacy), Postwick×4(スタジアム)。**全て非ex=単サイド**。
- 戦績: vs lucario_ex **0.69**(11-5) / vs **crustle_control 0.70**(7-3) / vs mixed_ex 0.71。
  → **ex ビートと anti-ex 壁の両方に勝つ**。

### shu（LB #13, 1166）= Lucario-ex（洗練版）
- デッキ: Mega Lucario ex×4 + Hariyama/Makuhita/Solrock/Lunatone/Riolu(非ex tech) +
  Dusk Ball×4/Premium Power Pro×4/Fighting Gong×4/Carmine×4/Lillie's Determination×4。
  我々の LUCARIO_DECK より trainer が充実した競技リスト。
- 戦績: vs **crustle_control 0.80**(8-2) / lucario_ex ミラー 0.58 / **vs non_ex_attackers 0.43**(3-4)。
  → Crustle を食い、ex ミラーは我々v003(0.31-0.47)より上手いが、**非exに負ける**。

### 三すくみ（確定）
非ex アタッカー → 勝つ → {ex ビート, anti-ex 壁} ／ ex ビート → 勝つ → 壁 ／ 壁 → 勝つ → ex ビート。
**頂点 = 非ex**（サイド1枚＋Safeguard貫通で両壁/ビートに勝てる）。ただし上位 field もまだ ex 主体で
非ex は未飽和（charmq は数少ない非ex使いとして上位に）。

### 我々への含意
- **v004 Crustle / v003 ex は両方とも apex(非ex)に弱い**（Crustle は貫通され、ex はサイド負け）。
- 短期: 自分の rating 帯(~975)は 57% ex・非ex 9% なので v004 Crustle で登れる。
- 頂点到達には **非ex アタッカーデッキ（charmq の実リスト複製）** が必要 = 次実験(exp012)候補。
  操縦方策が課題（Crustle mimic と同様）。まず汎用方策で試し、ダメなら専用方策。
- shu のリストは ex ミラー操縦が上手い → v003 の ex-mirror 改善余地もあるが、非ex の方が天井が高い。
