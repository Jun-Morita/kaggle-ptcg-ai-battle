# PTCG 代表戦略の整理（意思決定 diff 解釈用フレーム）

- 取得日: 2026-06-21 / 対象: PTCG AI Battle（Simulation＋Strategy）
- 出典: TCG Protectors（prize trade / archetypes guides）, tcgmartlondon, flipsidegaming（下部リンク）＋本コンペの実測メタ。
- 用途: 上位リプレイの意思決定 diff を「これはサイドレース／テンポ／妨害」と読み解く語彙。模倣/カウンター設計の土台。
- 注意: 実世界の standard 構築は本コンペの限定プールに直結しない。**原理（prize trade, tempo, archetype 役割）**を使い、具体カードは本コンペ実測（[[このコンペのメタ]]）で裏取りする。

## 1. 中核レバー（勝敗を決める軸）

### A. プライズ・トレード / プライズ・マッピング ★最重要
- KO で取るサイド数: 通常ポケ=1 / ex=2 / VMAX=3。先に6枚で勝ち。
- **核**: 自分の KO で取るサイド ＞ 相手の KO で取るサイド（=有利なトレード）。
- **単サイドが多サイドに勝つ**: 単サイド(1)で ex(2-3)を倒し続ける＝サイドレース有利 → **本コンペ apex の非ex 単サイド攻撃**の理論的裏付け。
- プライズ・マップ: 相手の初手から「どのKO経路で6枚取るか」を設計。例 2-2-2 / 3-3 / 1-1-2-2。
- 盤面で妨害: **必要以上に多サイドポケをベンチに置かない**（相手のKO経路を作らない＝prize liability 最小化）。逆に相手へは「7枚目を取らせる」よう余計なKOを強要し、相手の Boss's Orders 等を枯らす。
- **状態依存ルール**: 先行(リード)なら五分トレードを避ける／劣勢なら五分トレードを強要。プライズ確認(サーチ時に山を見る)で「鍵札がサイド落ち」を把握し計画を調整。

### B. テンポ / セットアップ consistency
- 毎ターン攻撃を継続（手損・空ターンを避ける）。
- ドロー/サーチ機関で鍵札を素早く揃える＝consistency が上級者の差。
- 本コンペ対応: Dudunsparce「Run Away Draw」、Team Rocket Petrel/Hilda/Transceiver、Buddy-Buddy Poffin 等。**サーチで何を取るか**が回り方を決める（v008 の search-priority の根拠）。

### C. シーケンス（手順）
- **黄金律: コミット前に最大限の情報を得る**（ドロー→展開の順、サーチを先に切る）。
- 進化・エネ・道具の付け先・攻撃対象の順序で選択肢を最大化。

### D. 妨害（disruption）
- 手札妨害（Xerosic's Machinations＝相手手札を3枚まで捨て）、呼び出し（Boss's Orders＝ベンチを active に引きずり KO）、エネ破壊、デッキアウト誘発。
- Boss's Orders の使いどころ＝(1)詰めの最後のサイド (2)相手の未完成アタッカー/エンジンを除去。

## 2. アーキタイプと本コンペ・メタの対応

| 一般アーキタイプ | 特徴 | 本コンペでの実体 |
|---|---|---|
| **Aggro / beatdown** | 最速でサイドを取る、OHKO 重視 | ex ビート（Mega Lucario ex 等, 多サイド） |
| **Control** | 妨害・デッキアウト・ダメージ無効で耐久 | **anti-ex 壁**（Crustle Safeguard, ex 無効＋回復） |
| **Midrange** | 効率アタッカー＋妨害＋consistency, 主軸＋テック | Alakazam＋Dudunsparce(THIRD #3) 等 |
| **単サイド・アタッカー** | 1サイド攻撃で多サイドにレース勝ち | **非ex Hop's Trevenant（apex, Debauchery #1）** |
| **Combo** | 特定カード相互作用 | （現状目立たず） |
| **Spread** | ベンチに分散ダメージ→低HP多数を狩る | Dragapult ex（単サイド密集の counter 候補） |

## 3. 本コンペの三すくみ（canonical 翻訳）
- ex ビート（aggro）→ 勝つ → **壁(control)**？ いや: 壁が ex を無効化 → 壁 ＞ ex。
- 単サイド非ex → ① 多サイド ex にレース勝ち ② 非exダメージが Safeguard を貫通 → **非ex ＞ {ex, 壁}（apex）**。
- 非ex への counter = **spread**（低HP多数を分散で狩る）。ただし上位の洗練非ex(Trevenant増量/Cramorant)は spread 耐性を獲得しつつある。
- 動的に回転・収束する（実測: Crustle一色→ex復権→単サイド非exに収束）。

## 4. 意思決定 diff の解釈レンズ（次ステップ用）
上位の実選択と我々の方策が乖離したら、次の軸で分類:
1. **プライズ**: 相手より多く取る/取らせない選択か（Boss's Orders の対象、ベンチ展開の抑制、Cramorant の3-4サイド窓）。
2. **テンポ**: 攻撃継続・最速セットアップを優先しているか（空ターン回避、進化の前倒し）。
3. **サーチ標的**: tutor で何を持ってくるか（鍵札の優先順）。
4. **シーケンス**: ドロー→情報→コミットの順序。
5. **妨害**: Xerosic/Boss の使いどころ。
6. **prize liability**: 多サイドポケや engine を晒さない。

## 5. 模倣 / カウンターへの落とし込み
- **模倣**: 乖離の多い軸（特にサーチ標的・Boss対象・Cramorant窓）を方策パッチに反映（v009+）。
- **カウンター**: 上位の状態依存ルールの裏を突く。例: 単サイドの prize liability の薄さ＝spread で多数同時圧迫／engine(Snorlax,Dudunsparce)を Boss＋KO で剥ぐ／Cramorant の「相手サイド3-4限定」窓を外す（サイドを一気に進める or 遅らせる）。

Sources:
- [Prize Trade & Mapping (TCG Protectors)](https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-prize-trade-guide-advanced-prize-mapping)
- [Deck Archetypes: Aggro/Control/Combo/Midrange (TCG Protectors)](https://tcgprotectors.com/blogs/pokemon-deck-guides/pokemon-tcg-deck-archetypes-guide-aggro-control-combo-midrange)
- [Intermediate Strategy & Prize Trade (TCG Protectors)](https://tcgprotectors.com/blogs/pokemon-deck-guides/pokemon-tcg-intermediate-strategy-guide)
- [Mastering Strategy: Setup/Attack/Defend (TCG Mart London)](https://www.tcgmartlondon.com/guide-to-playing-pokemon-tcg/mastering-pokemon-tcg-strategy/)
- [Aggro/Mid-Range/Control framing (Flipside Gaming)](https://flipsidegaming.com/blogs/pokemon-blog/aggro-mid-range-control-wait-this-isn-t-magic)
