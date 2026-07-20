# kaggle-ptcg-ai-battle

[Pokémon TCG AI Battle Challenge](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle) に Claude Code で取り組むためのワークスペースです。

ポケモンカードゲームを自動対戦する **AI エージェント**を作り、その戦略を**レポート**にまとめるコンペです。
運用ルールは [`CLAUDE.md`](CLAUDE.md) に従います（仕様を先に固定し、知識は出典付き、実験は `workspace/` に分離、判断は日報と提出履歴に残す）。

## コンペ概要

対になる 2 つのコンペで構成されます。詳細は [`competition/overview.md`](competition/overview.md) を参照。

| | Simulation | Strategy |
|---|---|---|
| ID | `pokemon-tcg-ai-battle` | `pokemon-tcg-ai-battle-challenge-strategy` |
| 提出物 | AI エージェント (`.tar.gz`) | 戦略レポート (Writeup ≤2000語) |
| 賞金 | なし (Knowledge) | **$240,000**（8 Finalists × $30,000） |
| 締切 (JST) | 〜2026-08-17 | 〜2026-09-14 |

- **Strategy の評価軸**: Model Score 70%（明快さ・独創性・**安定性**・**運/初期状態への非依存**・LB成績）/ Deck Score 20% / Report Score 10%。
- **LB 上位は必須ではない**。安定して筋の通ったエージェント＋デッキ＋明快なレポートが賞金への道。
- そのため Strategy で勝つには、まず Simulation 用に強いエージェントとデッキを作る必要があり、**両コンペを一体で進めます**。

## ゲームエンジン

- 対戦は **cabt Engine**（kaggle-environments 用の PTCG シミュレータ）上で実行。API docs: <https://matsuoinstitute.github.io/cabt/>
- エンジンはコンパイル済み `cg` パッケージ（`libcg.so` / `cg.dll` を ctypes 経由）。
- エージェント I/F: `agent(obs_dict) -> list[int]`。
  - 初手は `obs.select is None` で 60 枚デッキ（Card ID の list）を返す。
  - 以降は各局面で選択肢 index の list を返す（`minCount ≤ len ≤ maxCount`、重複不可）。
- **前方探索 API** `search_begin / search_step / search_end` あり。相手の隠し情報を予測値として与えて先読みでき、MCTS / ルックアヘッドの基盤になる。
- レーティングは TrueSkill 系 N(μ,σ²)（μ0=600、勝敗のみ反映、最新 2 提出で最終評価）。

> エンジン本体とカードデータはコンペ提供物のため Git では管理しません（`data/`, `references/raw/` は `.gitignore` 対象）。
> 各自 Kaggle からダウンロードして配置してください（下記）。

## マッチアップ別知見

対戦相手アーキタイプごとの構造的事実・我々の勝率履歴・適用済みルールは
[`competition/matchups/INDEX.md`](competition/matchups/INDEX.md) に集約する（実験ディレクトリを跨いだ知見の一元化）。
新しいマッチアップ固有の発見は、都度ここに追記する（重複記録を避ける）。

## データ配置

```bash
# カードデータ
uv run kaggle competitions download -c pokemon-tcg-ai-battle-challenge-strategy -f EN_Card_Data.csv -p data/raw
uv run kaggle competitions download -c pokemon-tcg-ai-battle-challenge-strategy -f JP_Card_Data.csv -p data/raw

# サンプル提出一式（cg エンジン本体 libcg.so / api.py などを含む）→ data/sim_sample/cg/ に置く
# Simulation コンペの sample_submission/ を参照
```

配置先（このリポジトリでの想定）:

- `data/raw/` … カード CSV
- `data/sim_sample/cg/` … `libcg.so`, `api.py`, `game.py`, `sim.py`, `utils.py`, `__init__.py`
- `references/raw/kaggle_pages/` … Kaggle ページの md（overview / data / rules）
- `references/raw/official_notebooks/` … 運営公開ノートブック（RL/MCTS、ルールベース 4 デッキ）

## Quick Start

```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync
pre-commit install

# GPU 確認（RL/MCTS 路線で必要になる）
uv run python scripts/check_gpu.py
```

`uv sync` で `src/kaggle_agent_template/`（共有ユーティリティ: `repro.set_seed`, `metrics` など）が editable install されます。

## ローカル対戦ハーネス

任意の 2 エージェントを対戦させ、勝率 / サイド差 / 手数 / 1 手の思考時間を集計します。

```bash
cd workspace/exp001_harness
uv run python run_gauntlet.py 20      # random vs random
```

- `harness.py` … エンジン読込 + `run_match` / `run_gauntlet`（先攻後攻を入替えてバイアス相殺、例外エージェントは反則負け）
- `agents.py` … ベースラインエージェント
- 結果は `results/` に JSON で保存（`.gitignore` 対象）

## 進捗（2026-07-20 時点）

**🎉 v028が923.9でsilver圏内（~251位／cut 917.4=268位以内／5,378チーム）**。
**eligible = {v028 koff 923.9, v029 koff 907.5}**、LB=2枠のmaxなので現在**923.9**。
締切8/16（Simulation）・9/13（Strategy）、最終提出目標8/2。

**HOLD方針が実証されました**: v028は888.2→923.9（+35.7）と、**リロールせずに枠が自力でsilverを
跨ぎました**。07-19夜のv030提案（v028リロール）を実行していたら、この923.9を捨てていたことになります。
これは朝に修正した「固定点まわりのランダムウォーク」モデルの予測どおりの挙動です。

### レート補正モデルの修正 → 運用方針を「HOLD一本化」に（07-20）
- **「day1固定くじ」モデルを部分反証**（v029が 888→932→898 と変動＝同一ビルドの揺れ）→
  **「固定点まわりのランダムウォーク」モデル**へ更新。固定点koff≈915はほぼcut水準。
- → **v030（v028第2チケット化）提案を自己撤回**。リロールで得るものは薄い。
  **基本方針=両枠HOLD**。リロールは**片枠が<~820に落ち24-36h停滞**（低basinトラップ）のときのみ。
  経験則: day1-2 ≥850=健全 / <800=トラップ / 800-850=グレー。
- **スコアアップ経路を「外部採用の日次監視」に切替**（内部4軸が全close、我々の強ビルドは歴史的に
  全て外部採用）。採用ゲート固定=**silver帯加重 > 0.786（koff）, n=600 CRN, 退行なし, クラッシュ診断**。
- 週次/meta-watch: 自帯域Spidops>20-25%でv020発動（要新cg再ビルド）。
- 最終ペア（8/2）: 両枠健全なら原則追加提出なし（最終評価は試合継続＝真の強度＝koff×2）。
- **Strategyレポートは優先度低**（ユーザー判断）。スコアアップ検討に時間を割く。

### 07-20の決着（詳細: daily_reports/20260720.md）— ネガティブ23/24/25件目

- **exp068「相手予測」レバー測定（ユーザー提案）→ 開発しない（25件目）**。
  まず**説明の訂正**: 出荷中のkoffには**探索が1行もない**（`search_begin`等が0ヒット）。
  「探索レーン閉鎖済み」は不正確で、exp060が閉じたのは**ミラー限定**だった。
  pub1034の探索ON/OFFを実帯域8種でCRNペア測定 → **silver加重 ON 0.8626 / OFF 0.8377
  ＝ +0.0249**（ミラーの+0.037と同水準）⇒ **「相手予測も平坦」が帯域全体に一般化**。
  弱点も直さない（dragapultは探索ONでも0.425）。**決定的反証**: v025は局所**+0.062**の優位が
  あったのに実ラダーは884.1で頭打ち＝**局所ゲインが転写しなかった実測前例**。
- **exp067 対dragapult解剖 → 構造的と「検証」（24件目）**。負け重み分解で標的選定
  （シェア5.7%で全敗北の18.0%、かつ未解剖）。当初の仮定（特性ダメージ）は**外れ**——
  負け試合は被ダメージが**少なく**ミル速度も**速い**のに**自ターンが3.7回足りない**。
  真因は**koffの勝ち筋が1本しかないこと**（残プライズは勝敗問わず常に6.00＝プライズを1枚も取らない）
  ＝**1クロック vs 2クロックのレース**。この機構は dragapult(0.363) と pure_wall(0.190) を
  **1つで説明**し、dragapultは高度と共に増える(1100+で7.14%)ため**穴は登るほど広がる**。
- **exp066 公開「LB 950+」エージェント → 不採用（23件目）**: silver加重**0.5475**。
  **宣伝された探索が完全な死にコード**（MAIN判断122回すべて早期return、`search_begin` 0回）。
  著者の実順位は**4078位/506.1**でタイトル未裏付け。→ 新ルール: 採用スイープの第1フィルタに
  **著者本人のLB順位照合**、評価前に**主要機構のコールカウント計装**。
- **外部採用スイープ2件とも不採用**: 新LB#1 LumenLiquidity（Dragapult型, 0.581）は
  その後**1199→1110で#1から#11へ転落**し診断が裏付けられた。LB#4 kashiwashiraは
  **exp055検証済みリストと56/60枚一致**（障壁はデッキでなくパイロット、3度目の確認）。
  → **日次スイープの候補はパイロット付き公開物に限定**（成功3例が全てそれ）。
- **exp065（エネルギー基盤仮説）step 0で棄却**: 実測で**逆相関**（Hammerは我々の勝ちと相関）。
  レバー測定ファーストが10分で足切り、計算投資ゼロ。
- **exp054-I（v029 932→898解剖）**: ローテなし・新リークなし、真の技量~915、ドロップは揺れ。

**計測ミスの訂正（誠実性）**: exp067初版で存在しない属性名（`prizeCount`/`cardId`）を使い
1707スナップショット全てnull、HPドレイン帰属にもoff-by-one。両方修正して再走した数字が上記。
教訓＝**API属性名は推測せず実物を読む＋null率チェックを計装の標準手順にする**。

<details><summary>07-19の決着: 改善レーン全closure＋RL分類学完結（詳細: daily_reports/20260719.md）</summary>

### 07-19の決着: 改善レーン全closure＋RL分類学完結
- **exp064 Actor-Critic（21件目）**: BCクローン(top-1 0.78)が教師本人に**0.122**、探索OFF教師にも
  0.170＝BC残差が敗因。**「一致率0.78→勝率0.12」＝decision-match≠strengthの最鮮明な定量化**。
  PPO前に0.3日でキル。これで**全RL家系に機構付き決着**（22ネガ+exp041の限定ポジ）。
- **exp060 sNES（22件目）**: n=600新シードでCENTER 0.5050＝**重み地形は69次元結合でも平坦**。
  要因分析→**設計ルール新設**: ①「レバー測定ファースト」（最適化前に最大レバーで可動域測定
  ——事後測定で判明: ミラーは探索ON/OFFですら+0.037しか動かない構造だった）、
  ②「進捗追跡の固定シードで有意性を語らない」（held-outシード使い回しがz≈4の偽信号を生成、
  新シードで消滅）。一般化: 判定の統計だけでなく**目的の物理**（価値連鎖の可動域）を先にモデル化
  ——必須4段階手順を制定。

</details>

<details><summary>07-18の3本柱プラン（07-19に全レーン決着済み、クリックで展開）</summary>

### 複数デッキ方策改善（07-18方針決定）: 3本柱×各1改善レーン

| 柱 | 状態 | 改善レーン |
|---|---|---|
| koff LO | 936実証・**方策/リスト両軸で局所最適と確定**（exp054-G/exp063） | リロール運用のみ |
| pub-Alakazam | 884（ミラー律速） | exp060 sNES（走行中）＋**exp064 Actor-Critic**（Stage 0） |
| v020 Archaludon | 対Spidops0.95/対Starmie0.895（床） | exp062 計装プローブ（キュー） |

- **exp063 デッキGA NO-GO（20件目）**: koff自由枠のGA、n=600ゲートで-0.047に反転（選択ノイズを
  ゲートが捕捉）。クラッシュ遺伝子Hero's Cape特定・除外の診断法も確立。
  **exp058(重み)/exp059(リスト)/exp063(自由枠)の3軸で「成熟公開ビルドの結合最適性」を実証**。
- **exp064 Actor-Critic起動**（未試行の最後のRL家系、GPUフル利用）: Alakazamミラー特化、
  BC温間開始＋PPO KL係留・固定相手・勝敗報酬のみ。ゲートA=クローン0.45→ゲートB=ミラー0.55(n=600)。
  Stage 0コーパス生成中（16kミラー試合、skip=0）。
- 監視: **TR Spidops 1.4→12.3%急伸**（pilkwang、field全帯域）——自帯域シェアを次回/meta-watchで確認。

### 07-18の決着（詳細: daily_reports/20260718.md）

- **exp054-G 操縦検証（リロール前のユーザー要請）: 操縦リークなし**。105試合ターンレベル解剖
  ——攻撃スキップ≈0、勝敗差=攻撃可能ターン数（W5.3 vs L1.5）＝相手起因のアタッカー枯渇。
  負け筋の正体: **アビリティ打点はSafeguard/NZを素通し**（dddmd戦: 相手攻撃0回で盤面全滅）
  ＝デッキ構造の穴。テック対策はスタジアム競合＋deck⊗pilot結合＋再現不能の3ブロッカーで保留。
- **exp061ステップ0: チップ系の床再現は不成立**（gagacrow実リスト×床RVPにkoff 0.885、
  アビリティ2388回使用してもキルに組み立てられない）。専用パイロットは見送り、
  再訪トリガー=mixed_ex3>25% or koff新ドロー2連続低迷。実リスト資産は保持。

</details>

<details><summary>07-17の主軸: koff両建てリロール（クリックで展開）</summary>

### 現在の主軸: koff両建てリロール（07-17、ユーザー承認）

- v025 pub-alakazamは**884.1で律速**（43%ミラー帯で0.32）。修正の試みは**両軸ともNO-GO**:
  exp058（重みチューニング、18件目）＋exp059（Hammer×4実リスト移植、19件目、ミラーゲート0.273）
  → 「**調律済みパイロットはデッキ⊗重みの結合最適点**」が確定し、v025枠をkoffチケットへ転換。
- koff線はv023がsettled **936.7 > cut 919.4**を実証済み。silver帯のAlakazam増加
  （公開1034.6系統の新規参入が920-1030帯に流入）は、Alakazamを0.83-0.92で狩るLO/koffに追い風。
- **staff公式回答（disc726690）がリロール運用を裏書き**: マッチメーカーは新提出・高σを大幅優先
  ＝高止まりした枠は試合頻度が落ちて自然保護され、新チケットは高速で収束する。
- 監視中の穴: ライブでmixed_ex3に3-9（シェア14→20%）。実体はStarmie（0-3）/Iono/実Froslass変種。
  **exp054-F決着（警報なし）**: Star-mineの実60枚×床パイロットに koff 0.720／v020 0.895／
  pub1034 0.790（n=200 CRN）→ Starmieの脅威はリストでなくパイロット（deck⊗pilot則の再確認）。
  シェア増が続く場合の即応駒はv020（最厚マージン0.895）。

### exp060 = pub1034の69ノブ結合最適化（sNES）— 07-19にNO-GO決着（22件目、上の07-19節参照）

- 中間: best 0.55-0.59／pop平均 0.48-0.54（gen0の0.443から持ち上がり=弱い正の兆候）／
  centerはsanityのノイズ帯と未分離。~42分/世代、07-19朝(UTC)完了見込み。判定はn=600ゲートのみ。

- exp058（単ノブ）とexp059（デッキ軸）が閉じた後の**残る未検証軸=重み空間の結合移動**。
  目的関数はミラー勝率 vs stock（ラダーのミラー相手はほぼstock系統の子孫＝外部妥当性が高い。
  v025の不動点884を決めたのはミラー0.32×帯シェア43%）。
- 設計: 69次元対数乗数空間、sNES λ=12ミラードサンプリング、**世代内候補間CRN共有**で
  ランキングノイズ圧縮、center/sanityアーム追跡、resume可。40世代×n=150、~14h（CPUのみ）。
- 事前登録ゲート: 最良候補を新シードn=600で**ミラー≥0.55**→副作用4種退行なし→出荷検討。
  キルスイッチ: baseline+2SE超えゼロなら20件目のネガティブでclose（exp060/SESSION_NOTES）。

</details>

<details><summary>07-15〜16の主軸だったv025 = 公開1034.6 search-augmented Alakazam（クリックで展開）</summary>

### v025 = 公開1034.6 search-augmented Alakazam（07-15採用・07-17押し出し）

- 公開notebook（tientrum）の旧チェックポイントで、**本人提出が実ラダー収束値1034.6**（07-05）
  ——プールより強い証拠。安全レビュー済・出典明記・クラッシュ安全ラッパー。
- 補正プール（n=200 CRN）: 自帯域**0.800**／silver帯**0.854**（v023: 0.648/0.792）。
  純壁0.910（LOキラーを狩る側）・archaludon 0.865。**弱点: Alakazamミラー（実戦0.35）・
  crustle_LO 0.375・dragapult 0.36**。
- **我々のゲートを通過した初の探索持ち**: 調律済み重み表＋2-ply信念サンプリングbounded search
  （「探索は効かない」通説への限定的反例。レプリカmax_act 0.32s）。
- 初動84試合: archaludon 0.86（局所0.865とぴったり）・lucario 0.81・全体0.643。
- 提出時にv023（927-937、旧枠）を意図的に犠牲（ユーザー承認、「新規提出は古い枠を押し出す」制約）。
- 保険枝=v024（KO_OFFミル）。LOの不動点~925-950へ収束中。

### 07-15の主な決着（詳細は daily_reports/20260715.md）
- **exp055 TR Spidops再現 NO-GO**（床ゲート2/4不通過。ただしTRメタの正解=v020と判明）
- **exp056 学習タイブレーカー NO-GO**（17件目。公開コード系統が場を占めるため
  同型上位者は教師にならない——タイ破りまで我々と同一だった）
- **exp054-E** 対Alakazam乖離分解（半分はプール構成→修正、残りは場の私的改変→-0.2ヘアカット）
- 運用制約発見: **新規提出は常に古い方のeligible枠を押し出す**（skillに追記）

</details>

<details><summary>07-14時点の進捗: イダイナキバLO＋KO_OFF = v023（クリックで展開）</summary>

**当時のeligible = {v022 (v021複製), v023-lomill-koff (942.3)}**、v023は一時silver圏内（202位）。

### 当時の主軸: イダイナキバLO（Great Tusk山札破壊）＋KO_OFFパッチ = v023

1. **silver帯の初実測（exp054）**: silver境界(LB948.8)のtomatomatoの719リプレイから相手プールを
   抽出。silver帯は**Alakazam系40.6%+Archaludon26.4%=67%**の別世界（自帯域はlucario31%/crustle20%）。
   **高度微分**（登ると勝率が上がるか）が本質的指標で、LOミルだけが正（+0.137）、
   自帯域最強だったv016壁はsilver帯0.438に崩壊＝構造的に登れない → **v021-lomill提出**。
2. **KO_OFFパッチ（exp054-B）**: 計装＋反実仮想プローブでLOパイロットの`should_ko_mode`
   （レース判定）が回復無視の誤算で勝てるミルを捨てていると特定。**丸ごと無効化**で
   silver帯加重0.734→**0.792**（archaludon +0.147 z≈4.3、退行なし、n=300 CRN）→ **v023提出**。
   「調律済みパイロットにパッチは効かない」則の初の例外＝実態は**機能削除**
   （「シンプル＞洗練」4例目）。
3. **リロール運用**: LBはbest-of-2＋同一エージェントでも収束±400pt（disc712621実測）→
   最強ビルドの複製を2枠に置き、数日ごとに低い枝を再提出で引き直す（v022=その1本目）。
4. **デッキ天井はsilver超えを実測確認（exp054-C）**: 同一60枚のLO使い3人が現silver圏
   （MR.h 965/Takuma_Tsuji 938/Rafael G 923）。彼らのパイロットは改造版（一致0.34）だが
   単純模倣（ベンチ最小化）は反実仮想でNO-GO。**KO_OFFは彼らも持たない独自エッジ**。
5. **弱点クラスとトリガー監視**: LOの構造的弱点＝**非exアグロ**（Safeguard/Zoneがex専用のため
   素通り）。純壁0.12-0.19、TR Spidops 0-3が実例。発動条件: 非exアグロ>10-15%（現4%）/
   crustle・LO系>20%（現~7%）/ Starmie上昇（現~0%）→ 即応駒はv020 Archaludon（silver 0.668）。
   カウンターデッキ育成は実測の上で見送り（dragapult 0.567/壁0.438 << v023 0.792）。

</details>

<details><summary>07-13の基盤刷新: 帯域プール + 較正済みEloモデル + CRN（クリックで展開）</summary>

### 【最重要】評価基盤の刷新: 帯域プール + 較正済みEloモデル + CRN（exp052/exp053）

07-13に**評価方法そのものの重大な欠陥**を発見・修正した。これが現在の方針の土台。

**1. ローカル評価プールが実ラダーと別物だった（exp053）**
v020の実戦績が27-28(wr=0.491)と伸びず調査。**自分たちのリプレイから相手デッキ60枚を
まるごと抽出**（`exp053_bandpool/extract_band_decks.py`）した結果:
- `lucario_ex`(帯域シェア31%)のローカル代理は実物と**60/60完全一致**（＝差はパイロット/ノイズ）
- **`crustle_control`(シェア20%)は17/60しか一致していなかった**——実体は純壁型ではなく
  **Great Tusk LO（山札破壊）型**（公開notebook "I have one REAR card", LB1083.6）。
  **帯域の20%を、全く別のデッキで代理評価していた。**

**2. 較正済みEloモデルの獲得**
本物の相手で組み直した帯域プールで測ると、帯域加重勝率0.659 → Elo固定点
`settled ≈ 相手平均 + 400·log10(p/(1-p))` の予測レート**≈770**に対し、v016壁の実測LBは
**770.7**——ほぼ完全一致。**ローカル評価が初めて実レートを予測できるようになった。**
このモデルが示す事実: **silver(933)には「今の帯域で0.72」ではなく「より強い帯域で0.6+」が
必要**——登れば相手も強くなるため、プールの組み替えや現有デッキの選び直しだけでは原理的に届かない。

**3. CRN（共通乱数）導入 → 分散4.66倍圧縮（exp052）**
公開エンジンソースを精査し、全乱数が`config.deviceRand`1フラグで分岐済みと判明。
`Api.h::ApiBattleStart`**1関数のみ**のパッチ（環境変数`CG_CRN_SEED`でseed注入）で
決定的再現を実現（**ローカル評価専用ビルド、提出物の`cg/`は無改変**）。実ゲートで
分散比**4.66倍**を実測（PokéForge報告の4.88倍と独立に一致）。
**効果は即座に表れた**——下記のLOミル vs v016壁は非CRN(n=100)では「統計的引き分け」
だったが、CRNで分散圧縮したことで**有意差(z=2.77)として決着**した。

### 現在の主軸: LOミル（山札破壊）デッキへの移行検討

較正済み帯域プール + CRN で全候補を再ランキング（n=300, `eval_band_crn.py`）:

| 候補 | lucario_ex 31% | crustle_LO 20% | mixed_ex3 11% | alakazam 18% | archaludon 9% | dragapult 7% | **帯域加重** |
|---|---:|---:|---:|---:|---:|---:|---:|
| **LOミル**(公開) | 0.833 | 0.500(ミラー) | 0.787 | **0.873** | **0.687** | 0.297 | **0.685** |
| v016壁 | 0.807 | 0.890 | 0.810 | **0.240** | **0.170** | 1.000 | 0.646 |
| v019-searchpri3 | 0.760 | 0.910 | 0.420 | 0.920 | 0.160 | 0.160 | 0.655* |
| v020-archaludon | 0.680 | **0.290** | 0.900 | 0.830 | 0.510 | 0.580 | 0.604* |

*非CRN(n=100)値。**判定: LOミル 0.685 > v016壁 0.646（delta +0.039, z=+2.77）**——
LOミルはv016壁の2大リーク（alakazam 0.24→0.87、archaludon 0.17→0.69）を
**山札切れという勝ち筋**で埋める（壁は非ex相手に勝ち筋を持てない）。代償はdragapult(7%)のみ。

**重要な構造的整理**: LBは「eligible2件の**独立レートの最大値**」で、各レートはその
エージェント**単体の全帯域成績**。マッチアップごとの使い分けは不可能なので、
**「2枠の相互補完」という発想はLB上まったく意味がない**。silverに必要なのは
**「単体で強いエージェント1つ」**だけ——問題が単純化された。

（当時の次アクション「デッキ比率調整でdragapult穴を埋める」は07-13夜に実施し**全変種NO-GO**
——LOはレースデッキで回復札は両時計を進めない、Neutralization Zoneが機能負担、の機構解明つき。）

</details>

<details><summary>07-12までの経緯: v020-archaludon（「全員が負けるデッキに乗る」戦略転換）→ 帯域実測で撤回（クリックで展開）</summary>

07-12に「メタ頂点のArchaludonに乗る」戦略でv020を提出したが、これは**LBトップ勢
(taksai/tomatomato/ShumpeiNomura)の観測に基づく判断**であり、**自分たちの実レート帯
(700-770)のメタとは別物**だった（CLAUDE.mdの「メタプール≠ラダーメタ」の実例）。
帯域プールで再評価するとv020は3候補中最弱(0.604)、本物のLOデッキに0.290で大敗。
07-13にeligibleを{v016-wall, v019-searchpri3}へ2段階提出で戻した。

### exp049: Archaludonデッキ複製 → v020提出（当時の判断）
mixed_ex4/Archaludon(メタ16%)はLB#1 taksai(0.28)・tomatomato(0.25)・v016壁(0.22)が
全員負ける現メタ頂点——倒す研究でなく使う側に回った。ShumpeiNomura(LB 1083)のデッキを
複製したが、**exp025の公開専用pilot+自前Cinderace型**が最強（Nomura構成差し替えは劣化
=pilotが自前デッキに調律済み、deck⊗pilotの再確認）。n=200×6合計**4.625/6**
（v016壁0.825・v019 0.870含む、全マッチ0.645+、0エラー）——ローカル計測史上最強。
bare-execレプリカ0エラー確認の上v020として提出。v016壁は意図的ドロップ（v020が壁の
標的を上位互換でカバー）。詳細: [`workspace/exp049_archaludon/SESSION_NOTES.md`](workspace/exp049_archaludon/SESSION_NOTES.md)。

### exp048: Mega Starmie exパイロット高度化 → (b)ヒューリスティックは診断成功・強さ不動 / (a)BCは惨敗
taksai(LB#1)/tomatomato(948.8、537試合)は同一のMega Starmie/Froslass構成でcrustle壁を
**22勝2敗**——"ex_beatdown"は壁に強いStarmie系と壁に弱いKangaskhan系の2系統が混在すると
判明。**(b)ヒューリスティック**: 修正済みペアリングのdiff(`policy_diff_fixed.py`)で
SETUP_ACTIVE 0.58→1.00・TO_BENCH 0.30→0.62に改善したが対壁勝率は0.950→**0.933**でほぼ不動。
**(a)BC**(07-13, GPU解放後): 実ラダーリプレイ30,152決定/807試合で学習——単一決定精度は
0.645まで健全に上昇したが、**実戦勝率は0.05〜0.10**（汎用パイロット0.825・(b)0.933を
大幅に下回る）。**NO-GO（16件目の誠実な負の結果）**。原因はデータ規模（本線RLネットは
590万件の合成事前学習を経ているが、今回は3万件からゼロ学習）——「一致率≠強さ」則の
最も極端な再現。実運用の到達点は(b)の0.933で確定。

</details>

### exp047: SEARCH_PRI2手法の横展開 → SEARCH_PRI3(DISCARD) GO→v019として提出済み
SEARCH_PRI2(TO_HAND, v018出荷済み)と同じ「select文脈の学習済み状態条件付き差し替え」を
他の文脈へ横展開。`extract_selects_ctx.py`（任意context対応の一般化抽出器）でYushin Ito
リプレイをスカウト: **TO_BENCH**(2207決定/972試合)は候補3種のみでほぼ決め打ち、静的
最頻値0.910に学習モデルが届かず**NO-GO**。**DISCARD**(943決定/786試合、候補19種)は
静的ベースライン0.220に対し学習val top-1 0.34-0.42と有望、`SEARCH_PRI3`として同一
統合パターンで実装。**決定ゲート=paired vs v014**（別ビルド、swap_sides）:
n=200(0.510)→n=600(0.545, z=2.20)→**n=1000: 538-452-10, winrate 0.538, z=2.40**
——**SEARCH_PRI2自身の最終z(0.76)より明確に強い有意な結果**。**判定: GO**（ユーザー
提出承認待ち）。詳細: [`daily_reports/20260712.md`](daily_reports/20260712.md) /
[`workspace/exp047_pri_tobench/SESSION_NOTES.md`](workspace/exp047_pri_tobench/SESSION_NOTES.md)。

<details><summary>exp046: encoderへのクロスターン特徴追加（RL設計プラン3） → NO-GO（クリックで展開）</summary>

リベンジ窓フラグ(v011実績)+PrizeTracker確定プライズbag(exp019実績)をencoderに追加。
初回学習(pre5, 154万レコード)はeval_raw旧5合計1.980で低かったが**データ量がpre2比1/4
という交絡**があったため、ENC_V2の新語が既存25語の**末尾**に追加される設計を活かし、
生成済みレコードの末尾2語を切り落として「同一ゲーム・ENC_V2=0相当」のデータを
無料で再現(`strip_encv2.py`)。**同一データ量での直接対照**: ENC_V2なし(pre5b)が
val top-1(0.7875>0.7807)・eval_raw旧5合計(**2.140>1.980**、+0.16)の両方で明確に上回り、
**交絡なしでENC_V2はこの実装ではむしろ悪化させると確定**。本RLライン15件目の誠実な
負の結果。詳細: [`daily_reports/20260712.md`](daily_reports/20260712.md) /
[`workspace/exp046_richenc/SESSION_NOTES.md`](workspace/exp046_richenc/SESSION_NOTES.md)。
</details>

<details><summary>2026-07-11 時点の進捗（クリックで展開）</summary>

**eligible = {v016-wall (Crustle壁, resubmit), v018-searchpri2}**。v018はfield全マッチ
改善(+0.085)・paired n=1000でも一貫してプラス(z=0.76、有意ではないが本セッション最安定)
を根拠に出荷。v018投入でeligible(最新2件)がv017/v018に変わりv016-wallが一時的に
押し出されたため、同一ビルドで即再提出しeligible={v016-wall, v018}を確定（メタカウンター
の壁と改良された非exチェーンを同時にeligible化）。

シルバーカット確認（`kaggle competitions leaderboard`）: 4,773チーム中 **silver top238 =
933.4点**、現在798.3点(1175位)。締切は8/16（Simulation）・9/13（Strategy）で残り約5週間。

### メタ分析→Crustle壁(v016)を再投入、RLはpre3b(v017)へ更新 — 両方提出済み(PENDING)
`/meta-watch`で対戦相手のデッキを実復元したところ、**現メタの約45%がMarnie's Grimmsnarl ex
/ Archaludon ex系**（mixed_ex3/mixed_ex4）。Yushin Itoの実データでGrimmsnarl exは
crustle_control(壁)に0.26で大敗することは確定済み。Crustle壁(v004系)を対今メタ6マッチで
実測(n=100、0err): **grimmsnarl複製1.000 / dragapult 1.000 / ex_lucario 0.800 /
archaludon 0.220 / 非ex(v014) 0.080 / ミラー0.410、合計3.51**——v014系と完全に補完的。
v016-wallとして再投入。RL側もpre3b(専門家吸収済み、eval_raw 2.24>pre2 2.14)をv017-RLとして
更新（v015-fix4を置き換え）。詳細: [`daily_reports/20260711.md`](daily_reports/20260711.md)。

### exp044: dragapult床(0.17)攻略 — 2機構とも単発では有意差なし
Yushin旧提出(同型デッキ)は同じdragapultに0.48で勝つ。行動差分（進化ライン狩り+Mist盾）を
2つのenv-gatedパッチ(DRAG_SNIPE/DRAG_MIST)に実装したが、DRAG_SNIPEはフラット(0.165)、
DRAG_MISTはn=600でz=0.98と**両方とも有意差なし**——静的スコア定数1個では動かせないと判明。
詳細: [`workspace/exp044_dragapult/SESSION_NOTES.md`](workspace/exp044_dragapult/SESSION_NOTES.md)。

### exp043 v2: ペアリングバグ修正で「状態依存は学習不可」の結論が覆る → v018として出荷
07-10発見のリプレイ・ペアリングバグを踏まえTO_HAND抽出を再実装。val top-1が
**0.526(差なし)→0.861**(静的基準0.704、+0.157≈6.5σ)に改善——v1の否定的結論は
バグ由来と確定。`SEARCH_PRI2`としてv014チェーンに統合。**field n=200×5は合計2.755
(v014基準2.67、+0.085、全マッチ無壊滅)**。決定ゲートのpaired vs v014はn=1000で
**winrate=0.512、z=0.76**——有意水準には未達だがn=200/600/1000を通じ一貫してプラス
（exp043 v1 SEARCH_PRIのz消失、pre3bのz=-0.82反転とは対照的な安定性）。ユーザー判断で
**v018-searchpri2として出荷（COMPLETE）**。

### exp045: turn-beam終端の学習評価器（プラン2）v1 → NO-GO（exp033と同型の再発）
RL設計再考（行動・状態・報酬の3軸棚卸し、ユーザーと合意）の本命として着手。`tb_patch.py`に
`TB_VALUE=1`ゲートを追加し、turn-beamのタイブレーク(与ダメージ)をexp032/033の学習済み
価値関数に置換（プライズ差の第一キー・v014の検証付き上書き規律は不変）。field n=200×5:
**合計2.620(-0.05)**——archaludonが-0.06悪化し他の小幅な改善を打ち消した。exp033
（価値関数統合が壁/アンチexマッチアップを悪化させる）と同型のパターンが統合構造を
変えても再発、fieldの時点でNO-GO。詳細: [`workspace/exp045_tbvalue/SESSION_NOTES.md`](workspace/exp045_tbvalue/SESSION_NOTES.md)。

### RL設計の再考（行動・状態・報酬）— 合意済みプラン、3案とも決着（07-12時点）
報酬=終端±1が「探索が効かない/自己対戦雪だるま」の共通根、として合意した3プラン:
(1) SEARCH_PRI2(select文脈の学習差し替え) → **出荷(v018)**、(2) turn-beam終端の
学習評価器(TB_VALUE) → **NO-GO**（exp033同型の再発）、(3) encoder語追加(ENC_V2)
→ **NO-GO**（交絡なしで確定）。silver主砲はメタ対応(v016壁)のまま。
SEARCH_PRI2の手法を他のselect文脈へ横展開(exp047)した結果、**SEARCH_PRI3(DISCARD)が
GO**（paired vs v014 n=1000でz=2.40、SEARCH_PRI2自身より強い有意な結果、詳細は上記
07-12セクション）——提出はユーザー承認待ち。

</details>

<details><summary>2026-07-11 pre3b(GPU run_pre3.sh)の詳細（クリックで展開）</summary>

### exp041 RL: run_pre3.sh（GPU）完走 — ミラー優位は小標本ノイズと判明、13件目の誠実な負の結果
07-10のCPU先行フェーズ（実ラダー/専門家コーパス、Grimmsnarl統合）を受け、GPU空き次第の
2段階学習を実行。

- **pre3a**（安全な吸収）: 合成val top-1 0.8313でPASSも、eval_raw n=50旧5合計が2.060で
  pre2基準2.14に未達（mirror_revengeが0.576→0.340へ大幅悪化）。grimmsnarlは目標達成(0.660)。
- **pre3b**（Yushin専門家データ追加）: **専門家ホールドアウトtop-1が0.436→0.549まで改善**
  （非exミラーが0.402→0.498と最大の伸び）——専門家プレイを忘却なく吸収できる点は実証済み。
  eval_raw旧5合計は2.240に回復（crustle 0.860で参照超え、mirrorは0.500まで回復）。
- **決定打: ミラー限定paired vs v014（別ビルド、swap_sides）**: 最初のn=200で
  winrate(pre3b)=0.525(105-92-3)と方向的な陽性に見えたが、**追加n=400で0.463に反転**。
  **n=600合算の最終結果: winrate=0.483 (290-297-13)、SE≈0.020、z=-0.82**——優位は
  消失。ex_lucarioの悪化懸念(0.720→0.580)もn=200再測定で0.700に回復、n=50ノイズと確認。
  **結論: pre3bはv014に対する実質的な優位を示さず、出荷不可**。本RLライン13件目の
  誠実な負の結果（教訓: n=200の結果でも再現性確認なしに「方向的」と結論しない）。
  詳細: [`daily_reports/20260711.md`](daily_reports/20260711.md) /
  [`workspace/exp041_pilotnet/SESSION_NOTES.md`](workspace/exp041_pilotnet/SESSION_NOTES.md)。

</details>

<details><summary>2026-07-10 時点の進捗（クリックで展開）</summary>

### exp041 RL: silver圏へ向けた計画練り直し（GPU空き待ちのCPU先行フェーズ、07-10）
v015-fix4がラダーで勝率~0.54と健闘する一方、ローカル評価は合計2.14でv014基準2.67に未達。
GPUが数時間使えない制約下で、CPUのみで次の一手を準備した。

- **重大発見: Kaggleリプレイのアクション・ペアリングバグ**。`steps[t].action`は
  **1ステップ前のobsへの応答**であり、同ステップ対応だと範囲外インデックス4.05%・
  ラベルずれが発生（次ステップ対応で0%・公式行動空間への捕捉率100%を確認）。
  **exp043のTO_HAND抽出はこのバグを踏んでおり**、v1の「状態依存が学習できない」という
  結論は確定でなくなった（SEARCH_PRIのNO-GO自体は独立の実対局評価なので不変）。
- **分布ギャップ診断**（numpy推論・CPUのみ）: pre2 vs 自分(v014)の実ラダー決定はtop-1
  **0.798**（全アーキタイプで均一、合成val基準0.830とほぼ同水準）——「学習分布≠実戦分布」
  仮説は決定ラベルレベルでは弱いと判明。一方 pre2 vs **Yushin旧提出**(同型デッキ、LB1097)
  の決定はtop-1**0.436**（非exミラーが最低0.402）——Yushinの強み(ミラー0.77 vs 我々0.585)
  の在処と一致し、**教師(v014)を超えうる唯一のBC素材**と判明。
- **構築した資産**: 自分の実ラダー対局45,447レコード(`ladder_w9.pkl`)、Yushin専門家プレイ
  56,627レコード(`expert_w8.pkl`)、Grimmsnarl ex（新#1デッキ）をteacher_pool/datagen/eval系
  に統合し合成データ約90万レコードを生成中、GPU再開時の2段階実行計画(`run_pre3.sh`、
  決定ゲート=ミラーのpaired vs v014)。詳細: [`daily_reports/20260710.md`](daily_reports/20260710.md) /
  [`workspace/exp041_pilotnet/SESSION_NOTES.md`](workspace/exp041_pilotnet/SESSION_NOTES.md)。

### トップランカー・スカウティング続報: Yushin Itoが我々と同型デッキから離脱、Grimmsnarl exへ
Yushin Ito（旧LB#7 1097.2、我々と同一Hop's Trevenant非exデッキ）が**Marnie's Grimmsnarl ex
にデッキを乗り換えLB#1(1272.8)に急上昇**していたことを発見。全1000リプレイでの確定成績:
dragapult 0.92(n=26) / lucario_ex 0.80(n=61) / non_ex_attackers(**我々の型**) 0.71(n=251) /
**crustle_control 0.26(n=153)**——三すくみ（Grimmsnarl ex rush > 非ex攻撃 > 各種ex >
Crustle壁）が大サンプルで確定。v014をこのデッキの複製に当てると0.60(n=100、我々の生成操縦が
相手なのでYushin本人との対戦はより厳しい可能性)。analyze_adaptation.py/policy_diff2.pyは
「対象が我々と同アーキタイプ」という前提がデッキ乗り換えで崩れ使えないことも確認・記録。
詳細: [`competition/matchups/grimmsnarl.md`](competition/matchups/grimmsnarl.md) /
[`workspace/exp011_meta_watch/scout_yushin_0710.md`](workspace/exp011_meta_watch/scout_yushin_0710.md)。

### 公開notebook分析: 「BattleCore Compact Agent」— 新規アイデアなし
07-08分析済みの「PTCG Meta A Stable Submit」と実質同一エージェント（detect_matchup()・
Hop's Snorlax名指しBoss狙撃・crustle overridesが完全一致）と確認。自称"Arena Validation"も
自分のA/Bデッキ同士の内輪比較のみでCrustle/Hop/Lucario/Starmieという実際の相手には未検証——
我々のn=200×5固定プール＋ペア評価の方が厳格。新規採用アイデアなし。

</details>

<details><summary>2026-07-09/10 時点の進捗（クリックで展開）</summary>

### exp041 RL: v015提出をめぐる4連続ERROR→真因特定→COMPLETE（07-09〜10）
Phase2/3の生ネット+MCTS（合計2.14、v014基準2.67に未達を承知の上でユーザー承認済み提出）を
v015として提出したところ`Validation Episode failed`が4連続（numpy除去→act速度修正→
堅牢化、いずれも正しい修正だが的外れ）。以前保存済みのagent stderrログから
**真因を特定**: Kaggleの実行系(`kaggle_environments.agent.get_last_callable`)は
`main.py`をソーステキストとして`exec(code, env)`で直接execするため**`__file__`が
一切定義されない**。`npmcts_policy.py`が重みファイルの場所特定に`__file__`を使っており、
`agent()`定義前のモジュールレベルで即死していた。ローカルの検証ドライバ
（`importlib.spec_from_file_location`経由、`__file__`が自動設定される）はこの不一致を
検出できていなかった。`__file__`依存を除去し、検証ドライバも実ローダーを正確に
再現するよう恒久修正 → **v015-fix4がCOMPLETE、RLエージェントがラダーに投入された**。
詳細: [`daily_reports/20260709.md`](daily_reports/20260709.md) /
[`workspace/exp041_pilotnet/SESSION_NOTES.md`](workspace/exp041_pilotnet/SESSION_NOTES.md)。

### exp043: SEARCH_PRIパッチ = 2件目の「field評価≠ペア評価」ネガティブ
Yushinスカウト由来のTO_HAND優先度バグ修正パッチ。field評価(n=200×5)は合計2.760
（v014基準比+0.09）とポジティブだったが、**v014と全く同じ手順で別ビルドし直接対戦
させるペア評価では winrate=0.505（コインフリップ水準）**でNO-GO。field評価の相手
（探索なしのgust_policy参照）とv014自身（同じフルビーム探索）の差が原因と推定。
exp042に続く2件目の同型教訓により、`/scout-top`スキルに
「ペア評価（別ビルド）を必須の最終ゲートとする」を追記。

</details>

<details><summary>2026-07-08 時点の進捗（クリックで展開）</summary>

**eligible = {v014 turn-beam, v013 reply-guard}**（v012 799 押し出し）。**v014 = ターン全体プランナー**（検証付き上書きでターン内系列をビーム展開, crustle 0.765→0.905 +0.14）。

**exp040 Stage4は打ち切り、9件目の誠実なネガティブ確定**: 相手デッキ条件付け(`opp_deck`)＋crustle損失
重み付け＋ランダム教師の3点を実装したが、公平な比較(リプレイバッファ付き)でもcrustleはpool評価11回
全てで0.000のまま。軽量な介入では自己対戦RLのcrustleシャットアウトを解決できないと確定
（詳細 [`workspace/exp040_mctsv2/SESSION_NOTES.md`](workspace/exp040_mctsv2/SESSION_NOTES.md)）。

**exp041: AlphaGo型パイプラインで強化学習ブレイクスルー**（silver目標のため強化学習早期実装を優先する
方針転換、RL失敗9件を5つの根本原因に整理した上で設計）。核心は「学習データの生成を弱い自己対戦
traineeから切り離し、既に持つ強いルールベース(v014 turnbeam)に生成させる」こと。
- **Phase 1**: v014操縦の対局データを39,858試合・296万サンプル生成（skip 0件、行動空間の懸念を解消）。
- **Phase 2**: 公式transformerを教師あり事前学習。決定的ゲート（探索なし生ネットの実対局）で
  **合計1.660（同条件パイロット比67%）、crustle 0.720**——自己対戦RLで87回連続0.000だった
  crustleへの勝率が生ネット単体で解錠。競技開始以来、RL系で最大のポジティブ結果。
- **Phase 3**: MCTS載せで**合計1.880（+0.22）**——exp010/exp040は探索を増やすほど悪化していたが、
  **競技を通じて初めて探索がエージェントを改善**。
- 安い強化（sc感度・追加エポック）で6エポック版が**合計2.140（パイロット比86%、mirror 0.640は
  パイロット自身0.576を超過）**まで到達。
- **Phase 4 fine-tune(ft1) = 10件目の誠実なネガティブ**: gen50-55でピーク(合計1.55)後、
  gen140-220の80世代でcrustle/dragapultが恒久的に0.00へ収束（教師プールにtrainee自身の
  過去チェックポイントが混ざり、負けデータの自己増幅が再発）。ユーザー承認の上gen222で打ち切り。
  **出荷候補は引き続きPhase2/3の生ネット+MCTS(6ep+sc16, 合計2.14)**（詳細
  [`workspace/exp041_pilotnet/SESSION_NOTES.md`](workspace/exp041_pilotnet/SESSION_NOTES.md)）。
- **出荷経路 A3(numpy移植) = PASS**: 公式transformerの推論を`npnet.py`で純numpyに等価移植
  （蒸留でなく同一重み）。実データでパリティ検証(誤差1.3e-5, argmax一致500/500)、
  速度0.61ms/決定。torch蒸留問題は解消。
- **出荷経路 A1(ミラー限定ハイブリッド) = NO-GO**: Phase3のmirror優位(n=50, 0.640>pilot 0.576)
  はn=200で0.535に後退——小標本ノイズと判明、前提棄却。

**exp042: ベンチ規律パッチ = NO-GO**（Mogja Jスカウト由来のdeck→bench規律を移植、TO_BENCH
行動一致率0.23→0.69に上げたが n=200×5 強さ評価は合計2.520 vs v014基準2.670）。
**教訓「行動一致率の改善≠強さの改善」**をscout-topスキルに反映
（[`workspace/exp042_benchdisc/SESSION_NOTES.md`](workspace/exp042_benchdisc/SESSION_NOTES.md)）。

**スカウティング: 同一アーキタイプの上位者 Yushin Ito（LB#7, 1097, n=1000試合）を発見**。
我々の2大出血源で dragapult 0.48（我々0.17）/ ミラー0.77（我々0.585）。最有力ギャップは
TO_HANDサーチ優先度（我々はChoice Band/Bossを過剰、Lillie's/Mist Energyを過少取得）。
→ **exp043: パッチを手書きせずYushinの6,058決定から模倣学習**（純numpy推論で提出直載せ可能）。
v1は val top-1 0.526 ≒ 静的頻度表 0.514 — 状態依存は未検出。学習モデルでなく、既存の
手書き優先度表`_TO_HAND_PRI`の**具体的なバグ**（我々のデッキが採用するPostwick/Lillie's
Determinationの2枚が未登録＝最下位級スコア）を発見・修正する`SEARCH_PRI`パッチを実装。
field評価(n=200×5)は合計2.760(+0.09)とポジティブだったが、**v014との直接対戦（別ビルド
ペア評価）ではwinrate=0.505＝NO-GO確定**（exp042に続く「field評価≠真の強さ」の2件目、
詳細は上記07-09/10節）。

LB は 6/30 環境更新（48試合/日・random 10%・draw→timeout）で全体圧縮、メダル圏入口 ~1140。
スコア分散は公式スレで文書化（同一エージェント ±150-400）→ **±150 はノイズ・判定は +150 級 or 重複提出**。締切後 ~2週の継続対戦で確定するため **high-roll 釣りは無効、開発継続が最適**。

</details>

<details><summary>2026-06-25 時点の進捗（クリックで展開）</summary>

ローカル評価は固定相手プールへの平均勝率。**メタは三すくみで一周し、現フィールドは ex 復権**（ex 39% / 非ex 26% / Crustle 11% / Alakazam 11% / Dragapult 3%）。
**現状の eligible = {v011 revenge, v006}**（μ600 から再収束中。v011 提出で v010 が押し出し、v011 ⊃ v010）。
**⚠️ 最重要教訓（06-24）**: v006–v009 は**同一の非exデッキ**で操縦だけ違うのに、**ライブ score が操縦の高度化とともに単調低下**
（v006 1086 > v007 1045 > v008 946 > v009 938）＝**ローカル gauntlet 過学習(CV/LB乖離)**。**今後どの提出も「現 eligible ペアのライブ score を超えるか」で判断する**（ローカル勝ちは転移しない）。
**★中核発見: 操縦が #1 レバー**（#3 Mogja は同一デッキで+200LB）。全方策の模倣/学習は情報的に上限（6系統 generic 未満）。
**転移するのは「達人精読で実機構の漏れを発見→局所修正」する gust クラスのみ**:
- **v010 gust**（Boss's Orders で gust+KO の漏れ → ミラー vs v006 0.685＝Mogja に一致）
- **v011 revenge**（Hop's Trevenant「Horrifying Revenge」の **+100 機構**を pilot が flat30 で見落とし → window 検出で +50 → ミラー 0.45→0.505 / Crustle 0.73→0.78, exp023）。
**操縦の枯渇も実証（06-25）**: `pilot_gap_scan` の **take-when-legal** で「合法手単位では我々の打ち手はトップと一致、差は exposure/throughput」＝**単一カード patch クラスは枯渇**。残差は対局長（盤面結果の従属変数）。
**さらに exp024 で「throughput の正体＝操縦不能な tutor エンジン」と判明**: 新 #1 Yushin Ito は同じ非exだが TR tutor エンジン搭載。我々の方策で TR デッキを操縦すると field 0.46 < charmq 0.61（deck⊗pilot 6回目）＝**throughput ギャップは pilot 修正でも deck 採用でも閉じられない（真の情報境界）**。
残るレバー＝**Strategy レポート($240k)**。**本文 [`competition/report_writeup.md`](competition/report_writeup.md)（英語≤2000語, take-when-legal 証拠を §8 に統合）執筆済み**。
公式 disc 711737（engine リバースエンジニアリング）・711741（multi-deck）は**運営未裁定**＝我々の純ヒューリスティック＋公式エンジン＋最新2枠ヘッジの**再現性優位**を補強。

### 実験
| 実験 | 内容 | 結果 |
|---|---|---|
| exp001 | ローカル対戦ハーネス | 完了（~10ms/game, 先後入替, 例外=反則負け） |
| exp002 | ルールベース5種＋random 総当たり | 強さ序列確定（lucario_v2 0.680 がプール最強） |
| exp003–004 | Search 1手読み / AlphaZero 自己対戦 | 0.21–0.27 / ~0.03（素朴な探索・学習は非競争的） |
| exp005 | クラッシュ安全提出 | **v001**（LB 841.8） |
| exp006 / exp008 | 模倣学習(BC) / belief 探索(PIMC) | BC 0.389 / belief 0.417 vs placeholder 0.083（探索の価値は相手モデル次第） |
| exp007 / exp009 | メタ対策(リプレイ解析) / 専用 Crustle 方策 | **v003 anti-Crustle**(一時 LB1123) / v005 |
| exp010 | **RL 再挑戦**（Phase2/3） | **3重検証の誠実なネガティブ**（value 品質がボトルネック, 探索増で悪化）。打ち切り |
| exp011 | **メタ監視**（週次リプレイ解析・上位辿り） | メタの一周＆非exへの収束を実証。`/meta-watch`,`/extract-deck` 化 |
| exp012 | **非ex apex 複製＋専用方策** | **v006**(ex0.67/Crustle0.83) → **v007**(mirror0.775/ex0.725) |
| exp013 | **deck-dispatch 方策＋意思決定 diff** | **v008**(ex0.80/Crustle0.767, v007上位互換)。diff で乖離抽出も模倣(v009)は改善せず＝**ヒューリスティック上限** |
| exp014 | **オフライン RL value 較正**（実上位319試合, 試合単位 holdout） | **決定的ネガティブ(4本目)**: 中盤 AUC 0.64/0.59(<0.70)・終盤0.80。学習 value は中盤を当てられず＝deep RL は経験的に上限 |
| exp015 | **終盤の戦術的探索レイヤー**（自ターン正確探索, 学習なし） | ネガティブ: 3変種ミラー≤0.47＝正確探索も超えず。ただし**prize tracking で再評価余地**（exp019候補） |
| exp016 | **公開ノート3点分析**（5位Alakazam等） | **v008 vs Alakazam 0.90**（脅威でない）／公式 episodes 手がかり／Alakazam を評価プールに追加 |
| exp017 | **Dragapult メタ・タイミング評価** | 単サイド収束で spread を検討も、**実物スモークで不提出判定**（ex0.19/Crustle0.0）。教訓: ローカル混載 eval は汚染 |
| exp018 | **トップ適応分析＋規律パッチ** | トップ edge = **相手別切替でなく bench 規律** → **v009**（非exミラー vs v008 **0.55(n=200)**, ローカル上位互換）。提出 |
| exp019 | **prize-aware 検証リーサル finisher** | ネガティブ: ミラー0.53（有意差なし）。prize tracking で exp015 の偽リーサルは除去できるが、1KO/ターン型には不要 |
| exp020 | **デッキ革新(Tinkaton)＋強Dragapult脅威** | Tinkaton アンチミラー失敗(S2 不操縦, ミラー0.00)＝pilotability 律速。強Dragapult は v009 を0.78で狩るがメタ封じ込め0.47 |
| exp021 | **setup-bench 規律**（disc708586） | ネガティブ: 我々の basic-light デッキでは no-op（base 平均1.41体, cap 不発, ミラー0.50±）。レバーは basic-heavy 専用 |
| exp022 | **操縦研究**（トップ模倣／Mega Starmie／RL再挑戦／**局所改善**） | **★操縦が #1 レバー**: #3 は同一デッキで+200LB。全方策模倣は情報的上限（6系統 generic 未満）だが、**高レバレッジ局面の局所改善は有効**＝Mogja 精読で「Boss's Orders gust」漏れ発見→修正で**ミラー vs v006 0.685(==Mogja)**＝v010 提出 |
| exp023 | **実戦略由来の操縦高度化**（revenge-window 機構）＋ **pilot_gap_scan**（take-when-legal） | **take-when-legal で単一カード patch 枯渇を実証**（合法手採用率はトップと一致, 差は exposure）。だが**攻撃評価軸は未監査**＝Trevenant「Horrifying Revenge」の +100 機構を pilot が見落とし → window 検出で +50（subprocess隔離スイープ, n=200 ロバストゲート, RB=50 最良）→ **ミラー 0.45→0.505 / Crustle 0.73→0.78** = **v011 提出** |
| exp024 | **新 #1 の TR-エンジン操縦 feasibility**（Yushin Ito 1387 = 同じ非exだが tutor エンジン） | **ネガティブ（deck⊗pilot 6回目）**: TR デッキを我々の best 方策で操縦＝**field ~0.46（ex 0.54/mirror 0.33）＜ charmq v011 0.61**。setup 速度は正常（初撃 turn3.6）＝中盤エンジン活用＝情報境界。`_score_to_hand` 拡張は退行（ex 0.54→0.40）。**頂点の throughput 優位は操縦不能な tutor エンジン**＝take-when-legal をデッキレベルでも裏付け。TR 乗り換えは負け |

### 提出（eligible = 最新2提出, 2026-06-25）
> **⚠️ CV/LB 乖離**: 同一デッキで操縦“高度化”しても以前はライブ score 低下（1086→…→938）。ローカル勝ちは転移しない。**v010/v011 は gust クラス（実機構修正）の転移を試す検証提出**。

| 版 | 中身 | 状態 |
|---|---|---|
| **v011 revenge** | v010 gust ＋ **revenge-window 機構**（Hop's Trevenant Revenge +100 を window 検出で +50 modeling）。ミラー 0.45→**0.505** / Crustle 0.73→**0.78**（n=200, 0err） | 提出(PENDING, μ600, sub 54044198)。**gust クラスの転移を検証中** |
| **v006** | charmq 非ex ＋ generic（自己最良） | 再提出(PENDING, μ600)。退役前 **1086.7**。安全側アンカー |
| v010/v007/v009/v008 | gust/専用/規律/dispatch | v010 は eligible 枠外（v011 ⊃ v010）。他は退役 |

### 中心的発見
- **メタは三すくみで一周し、収束する**: ex ビート → Crustle 壁 → **単サイド非ex** → …。06-18 Crustle 一色 → 06-20 ex 復権 →
  上位は**単サイド非ex に収束**（Hop's Trevenant / Alakazam。単サイドで ex にレース勝ち＋Safeguard 貫通）。
- **リプレイ駆動のメタ分析が最重要レバー**: 自分＋上位の試合を解析し、回転に追従して提出（v003→v004→v006→v007→v008）。
- **デッキ⊗方策は密結合**: #1 のリストを複製しても我々の方策では回らない(ex 0.167)。我々が回せる charmq デッキが現実解。
  汎用方策＋的を絞ったパッチ（攻撃モデル/サーチ優先度）で v003→v008 と改善。
- **方策はヒューリスティック上限に到達**（3方向で一致）: ①RL 3重ネガティブ ②v008 後のミラー微調整が無効 ③意思決定 diff で
  上位の選択を模倣しても勝率不変（ミラーは対称~0.5、乖離選択の多くは等価に good）。**価値は学習でなく推論時の探索＋相手モデル**。
- **相手モデル(determinization)が探索の価値を決める**（exp008, 対照実験 belief 0.417 vs placeholder 0.083＝5倍）。
- **学習も探索も実証で上限**: ①exp014＝実上位319試合でも value 較正は**中盤を当てられない**(AUC<0.70, 終盤のみ0.80)＝
  exp010「探索増で悪化」を機構的に説明 ②exp015＝**正確な near-terminal 探索すら**ヒューリスティックを超えない(ミラー≤0.47)。
  → 中位資源では「メタを読む rule-based＋良い操縦」が achievable ceiling。
- レポート: **本文 [`competition/report_writeup.md`](competition/report_writeup.md)（英語・提出物）** / 草稿 [`competition/report_draft.md`](competition/report_draft.md) /
  数値台帳 [`competition/report_evidence.md`](competition/report_evidence.md) / 戦略リファレンス [`references/knowledge/ptcg_strategy.md`](references/knowledge/ptcg_strategy.md)。
- ⚠️ **CV/LB 乖離（06-24 監査）**: 同一デッキで操縦を高度化するほどライブ score が単調低下（v006 1086→v009 938）＝ローカル gauntlet 過学習。
  **ローカル勝ちはラダーに転移しない**（v007/v008/v009 全て local 勝・live 負）。今後の提出は**現 eligible ペアのライブ score 超過**で判断。
- ⚠️ ラダーは「最新2提出(時刻順)のみ最終評価」。改良版の提出は最良エージェントを**無言で退役**させ得る。最良ペアを最新枠に死守すること。

</details>

### 実験（06-26 以降）
| 実験 | 内容 | 結果 |
|---|---|---|
| exp025-026 | Archaludon 対策（un-KOable 誘導 / Neutralization Zone / Crustle counter） | 全滅＝**構造的に不利**（HP300+220確殺+非exバイパス）。ただしメタから自然減衰 |
| exp027 | **デッキ比率最適化**（Trevenant 2→4） | 全マッチ改善(n=200, mirror +0.12) → **v012**。ラダーは v011 と同点＝比率レバーも頭打ち |
| exp028 | #1 Debauchery（Grimmsnarl ex rush）抽出・脅威判定 | v012 が複製に 0.68 = 対策不要。1350 との差はマッチアップでなく一貫性 |
| exp029 | **相手応手ガード**（K=4 belief rollout, 全K破滅時のみ拒否権） | ex_lucario 0.77→**0.86** 有意・全マッチ無退行・<1%時間 → **v013 提出（初の本番探索層）** |
| exp030 | 公開 Great Tusk LO（mill, 1083.6）脅威測定 | **0.82 で非脅威**（Safeguard/NZ は ex 攻撃のみ無効＝完全非ex の我々に無風）|
| exp031 | exact revenge window（**エンジンソース準拠**の窓検出） | 単独 crustle +0.085 も guard 統合で消失→見送り。**近似 proxy の偽陽性が偶発的に有益**という発見 |
| exp032 | **ネイティブエンジン→20万試合→価値較正再テスト** | **中盤 AUC 0.806 = exp014「学習不能」を覆す**（319試合はデータ律速だった）。純numpy MLP に蒸留 |
| exp033 | value-guided guard（価値ネットで候補上書き, margin 0.10） | **doom 拒否権に及ばず**（2.505 vs 2.58）。壁マッチで近視眼＝**変換可能性は統合律速**。OOD 修正(8デッキ再学習)でも不変 → 価値ライン終結 |
| exp034 | 対 Dragapult ゲート付きベンチ規律 | 無効(0.200)。**レース算術で機構特定**: HP320/確殺200 に素130は3発、勝ち筋=+30成立で160×2 |
| exp035 | **turn-beam**（ターン全系列のエンジン探索、プライズ+ダメージの全K検証付き上書き） | 常時上書き版は大退行(0.30)→検証付きに再設計。n=200 で **crustle +0.14 / 合計2.67>v013 2.58** → **v014 提出** |
| exp036 | GA による操縦定数の進化（ラダーシェア加重プール, グローバル→マッチアップ別想定） | **打ち切り**: n=200 厳密検証でチャンピオンが基準級に崩壊(2.48)。小サンプル(n=48/個体)フィットネス過学習＋「GAは定数調整止まり」の上限 |
| exp037 | turn-beam の探索予算拡張（beam/branch/maxsteps/K スイープ） | ネガティブ/中立: 合計2.650≈v014 2.670（誤差内）。予算拡張は頭打ち＝設計の問題 |
| exp038 | **depth=2 alpha-beta 探索**（自ターン+相手応手, 相手アーキタイプ模倣, 拡張評価関数, probe順序付け） | 3ラウンドの系統的デバッグで実バグ**11件**（root比較/状態汚染/予算非対称/地平線効果3種/手札推定/相手モデル状態汚染/試合跨ぎ状態漏れ/クラッシュ等）を発見・修正。n=40確定検証で**全マッチ基準以下・合計1.575<<基準2.45**＝**誠実なネガティブ・不採用** |
| exp039 | v014+v013由来ガード(doom-veto)+exp038相手モデルの合成 | n=100でfield total 2.63（v014の2.67と統計的パリティ）。archaludon検知ガードは意図通り機能したがex_lucarioの改善は再測定で消失＝**DO NOT SHIP、v014維持** |
| exp040 | **公式RL/MCTSサンプルへの回帰**（決定化バグ修正+ネイティブエンジン+teacher-assisted self-play+リプレイバッファ→gen400で打ち切り→opp_deck条件付け+crustle損失重み+random教師） | Stage2はgen400(20%予算)でlossは低下も**crustleは76回中0勝**。Stage4(相手デッキ明示条件付け+損失重み+ランダム教師)も公平な比較でcrustle 11回全て0.000＝**打ち切り、9件目の誠実なネガティブ確定** |
| exp041 | **AlphaGo型パイプライン**（v014操縦データで教師あり事前学習→MCTS→自己対戦fine-tune） | Phase1(39,858試合・296万サンプル)→Phase2ゲートPASS(**crustle 0.720**、自己対戦RLの0.000から解錠)→Phase3ゲートPASS(**MCTS+0.22、競技初の探索改善**)→6epで合計2.140(パイロット比86%)。**Phase4 fine-tune(ft1)はgen140-220でcrustle/dragapult恒久0.00に劣化=10件目のネガティブ、gen222打ち切り**。データ倍増+opp_deckドロップアウト(A2)→合計2.14で頭打ち、DAgger v2で2.20まで小幅改善。**v015としてユーザー承認の上提出→4連続`Validation Episode failed`→真因は`__file__`未定義（execベースローダー）→修正しv015-fix4でCOMPLET、ラダー投入成功** |
| exp042 | ベンチ規律パッチ（Mogja Jスカウト由来、deck→bench効果で1枚だけベンチ） | TO_BENCH行動一致0.23→0.69だが n=200×5 で**合計2.520 < v014 2.670 = NO-GO**。**教訓「行動一致率≠強さ」**をスキルに反映 |
| exp043 | **学習されたサーチ優先度**（同型上位者Yushin Ito n=1000試合のTO_HAND 6,058決定から模倣学習、純numpy推論） | v1: val top-1 0.526 ≒ 静的頻度表 0.514＝状態依存は未検出。手書き表のバグ修正パッチをfield評価(合計2.760, +0.09)→**ペア評価(別ビルド, winrate=0.505)でNO-GO**。**教訓「field評価≠ペア評価」2件目** |

### 提出（eligible = 最新2, 2026-07-09/10）
| 版 | 中身 | 状態 |
|---|---|---|
| **v015-fix4** | exp041 AlphaGo型RLパイプライン（pre2 raw argmax、numpy-free、`__file__`不使用） | **提出済・COMPLETE**（μ600収束中）。RLフィードバック・真のレート測定が目的。ローカル合計2.14-2.20（v014基準2.67に未達を承知の上でユーザー承認済み提出）|
| **diag-probe (v014クローン)** | v014のmain.pyそのまま＋未使用の診断用重みファイル | 提出済・COMPLETE（score 812.5）。v015調査の副産物、実質v014のセーフティネット |
| v014 turn-beam / v013 reply-guard | 直近まで出荷済み最良ペア（eligible枠外に一時退避） | crustle 0.765→0.905(+0.14) / 合計2.67。**RLフィードバック収集期間終了後、枠奪還を検討** |

### 中心的発見（06-26 以降の追加）
- **探索は「検証付き・拒否権」の形でのみ勝つ**: 常時上書き（exp035 初版0.30）・価値誘導（exp033）は
  チューニング済みヒューリスティックの多ターン計画を壊す。全K検証の doom 拒否権（v013）だけが無退行で上積み。
- **エンジンソース公開の活用**: ①機構の答え合わせ（revenge=koAttackDamageHop, 偽陽性の機構解明）
  ②ネイティブビルドで大規模データ生成 ③「観測→推定→ソース検証」はレポートの再現性の物語。
- **「学習可能性はデータ律速、変換可能性は統合律速」**（exp032/033）— RL 6連敗の正確な再解釈。
- **床マッチは piloting で救えない**（exp034 レース算術）。負けの53%は構造（Dragapult/Archaludon）。
- **ラダー分散 ±150-400 は公式スレで文書化**（同一エージェント重複提出の実測）。判定閾値 +150 級。
  締切後 ~2週間の継続対戦で確定 → 最終スコア ≈ 真の実力 ＝ 釣りより開発。
- 運用: 長時間評価は**20試合チャンク＋マーカー再開**（run_chain.sh 標準化）。探索内で実対局 policy
  インスタンスを呼ぶと内部状態が汚染される（必ず別インスタンス）。

### 週次運用（スキル化済み）
```bash
/meta-watch                # 何が流行か: メタ分布＋回転検知＋LB（exp011 meta_watch.py）
/scout-top                 # どう打つか＋我々の差: 相手別挙動＋決定diff→チューニング標的（exp018 analyze_adaptation.py）
/extract-deck <sub_id>     # 任意選手の正確な60枚を複製（exp011 extract_deck.py）
/build-submit              # デッキ+方策→ビルド→実物スモーク→承認後提出（scripts/build_submission.py）
# 検証は n≥200＋ペア比較＋実物スモーク（小サンプル/混載 eval はノイズ・汚染）: exp018 eval_mirror.py / eval_compare.py
```

各実験は 1 ディレクトリ 1 仮説で `workspace/expNNN_name/` に分け、`SESSION_NOTES.md` に仮説・変更・結果・出典を残します。
その日の判断と次アクションは `daily_reports/YYYYMMDD.md` に集約します。重い生成物（`.pth`、提出 bundle、抽出した競技/3rd-party コード）は Git 管理外。

## 提出

- Simulation: `main.py`（トップレベル）＋ `deck.csv`＋`cg/` を `tar -czvf submission.tar.gz *` で固めてアップロード。
- Strategy: Kaggle Writeup（≤2000語）＋ Media Gallery。
- Kaggle への実アップロードはユーザー承認後に行います。提出したら `submit/SUBMISSIONS.md` と `submit/submissions.csv` に記録します。

## Check

```bash
uv run python scripts/check_gpu.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
