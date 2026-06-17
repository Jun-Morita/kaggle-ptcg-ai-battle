# Notebook Knowledge

Public notebook から得た知識を要約する。

## Entries

```markdown
## YYYY-MM-DD: title

- Source:
- Fetched at:
- Author:
- Competition:

### Key Ideas
- 

### Useful for This Competition
- 

### Risks / Caveats
- 

### Experiment Candidates
- 
```

## 2026-06-17: 運営公開ノートブック5本（raw: `references/raw/official_notebooks/`）

- Source: Simulation コンペ公式（`pokemon-tcg-ai-battle`）
- Fetched at: 2026-06-17 / Author: PTCGABC Team

### A. RL & MCTS sample (`reinforcement-learning-and-mcts-sample-code.ipynb`)
**AlphaZero 系の完全な自己対戦学習リファレンス。** これがRL路線の出発点。
- モデル: Transformer encoder/decoder + `EmbeddingBag`（スパース特徴）。value ヘッド(encoder)+policy ヘッド(decoder)。
- 特徴設計: 盤面(両者bench×8, active, player状態, 手札, 自デッキ, スタジアム, ターン)をスパースベクトル化。actionは OptionType ごとに decoder 特徴へ。
- MCTS: Search API (`search_begin/step/end`)で前方展開。PUCT (c=0.4·√visit)、最多訪問選択。葉でNN評価しbackprop。`SEARCH_COUNT=10`（デモ用、小さい）。
- 学習: 自己対戦→TD(λ=0.9)で value ラベル付け→Huber損失で value/policy 学習。5世代ループ。
- **determinization が雑**: 自分deck/prizeはdeckからランダム、相手はSnorlax(id1072)/基本エネ(id1)で穴埋め（相手モデル化なし）。→ ここは改善余地。
- 探索の副産物: 「今攻撃したら実際何点入るか」等を Search API で確定できる。**ルールベースにも有用**と明記。
- デッキ検証エラー: 1=不正ID, 2=同名5枚以上(基本エネ除く), 3=基本ポケモン無し, 4=ACE SPEC 2枚以上。

### B. ルールベース agent 4種（4つの完成デッキ付き）
共通フロー: obs受領→合法手(select.option)列挙→各手をスコア→最高スコアを返す。Dragapult版は864行で最も精緻（カード個別知識・サイド交換評価 `prize_count/pokemon_score`・付与/手札スコア・ターン依存ヒューリスティック）。
**4つの合法デッキ（baseline/対戦相手/Deck Score 参照に直接使える）:**
- **Dragapult ex**（攻撃的・Crispin×4で早期攻撃）: Dreepy119×4, Drakloak120×4, Dragapult_ex121×3, Fezandipiti_ex140, Latias_ex184, Budew235×2, Meowth_ex1071, Rare_Candy1079×2, Unfair_Stamp1080, Buddy_Buddy_Poffin1086×4, Night_Stretcher1097×2, Crushing_Hammer1120×4, Ultra_Ball1121×4, Poke_Pad1152×3, Lucky_Helmet1156, Boss_Orders1182×3, Crispin1198×4, Brock_Scouting1210×2, Lillie_Determination1227×4, Team_Rocket_Watchtower1256×2, 基本炎2×4, 基本超5×4。
- **Iono's Bellibolt ex**（エネ大量付与で Voltaic Chain 高火力）: Iono_Voltorb265×3, Tadbulb268×3, Bellibolt_ex269×3, Wattrel270×3, Kilowattrel271×3, Buddy_Buddy_Poffin1086×3, Night_Stretcher1097×2, Max_Rod1110, Energy_Retrieval1118, Ultra_Ball1121×3, Poke_Pad1152×2, Lillie1227×4, Canari1233×4, Levincia1254×3, 基本雷4×22。
- **Mega Abomasnow ex**（Hammer-lanche=デッキトップ6枚discardの水エネ枚数×100）: Kyogre721×2, Snover722×4, Mega_Abomasnow_ex723×4, Ultra_Ball1121×4, Precious_Trolley1126, Carmine1192×4, Lillie1227×4, Surfing_Beach1262×3, 基本水3×34。
- **Mega Lucario ex**（状況適応: Lucario/Hariyama/Solrock 使い分け）: Makuhita673×2, Hariyama674×2, Lunatone675×2, Solrock676×3, Riolu677×3, Mega_Lucario_ex678×4, Dusk_Ball1102×4, Switch1123×2, Premium_Power_Pro1141×4, Fighting_Gong1142×4, Poke_Pad1152×4, Hero_Cape1159, Boss_Orders1182×2, Carmine1192×4, Lillie1227×4, Gravity_Mountain1252×2, 基本闘6×13。

### Useful for This Competition
- 4デッキ＋4 agent をそのまま **評価相手プール（gauntlet）** にできる。ランダムより遥かに強い対戦相手。
- Dragapult agent のスコアリング構造を雛形に、自前ルールベースを高速に作れる。
- RL/MCTS は最終的な強さの本命。Search API の正しい使い方（determinization, PUCT, search_release）が学べる。
- Strategy の Deck Score 用に、これらデッキを分析・改良した独自デッキを設計する材料。

### Risks / Caveats
- 公開コード＝全員が使える。差別化には改良（determinization 改善, 相手モデル化, デッキ調整, 探索強化）が必須。
- MCTS サンプルの相手穴埋めは非現実的。本番性能には相手分布の推定が要る。
- ルールベースは公式も「単体では上位困難」と明言。探索/学習との組合せが必要。

### Experiment Candidates
- exp002: 4ルールベース agent を移植し、gauntlet で相互勝率＋対ランダム勝率のベースライン表を作る。
- exp003: Search API で1手読み（「攻撃の実ダメージ/勝敗」評価）を入れた軽量agent。
- exp004+: MCTS サンプルを動かし、determinization と相手モデルを改善。

## 2026-06-17: [Beginner Guide] From Deck List to First Valid Sub（public, raw: `references/raw/public_notebooks/`）

- Source: 公開ノートブック（kiyotah の公式 Mega Lucario サンプルがベース）。LB Score **770.4** / Bronze。
- **agent・デッキは公式 Mega Lucario サンプルそのまま（未改良）**。価値は提出手順とベースライン値。

### Key Ideas / Useful
- **提出パッケージング手順**（`tarfile` で `submission.tar.gz` を作る）:
  - `deck.csv`（60行のCard ID, ハードコード or dataset から読む）を書く。
  - `main.py`（agent）を書く。`deck.csv` は `deck.csv` がなければ `/kaggle_simulations/agent/deck.csv` を読む。
  - `cg/` フォルダを input から glob で探す（`/kaggle/input/**/sample_submission/cg` 等）。
  - `tar.add("main.py", arcname="main.py")` ... `tar.add(cg_path, arcname="cg")` で **main.py をトップレベル**に。
  - 提出前に `tar.getnames()` で中身（main.py がネストしてないか）を確認。
  - 提出は Save Version → Save & Run All (Commit) → Output 確認 → Submit が安全。1日5回まで（UIに `n/5 used`）。
- **ベースライン LB 基準**: 公式 Mega Lucario デッキ＋ルールベース = **770.4**。ローカル勝率↔LB の校正点として使える（μ0=600 スタートに対する到達点の目安）。

### Risks / Caveats
- 中身は公式サンプルと同一なので、これ自体に強さの上積みはない。差別化はデッキ/agent 改良が必須。
- ハードコードデッキは公式 Mega Lucario と同一構成（673×2,674×2,675×2,676×3,677×3,678×4,1102×4,1123×2,1141×4,1142×4,1152×4,1159×1,1182×2,1192×4,1227×4,1252×2, 闘6×13）。

### Experiment Candidates
- exp002 の提出フローに、この `tarfile` パッケージング手順を流用する（`templates/submit_kernel/` を PTCG 用に更新）。

## 2026-06-17: Validated Rule-Based Agent + Matchup Tests（public, raw: `references/raw/public_notebooks/`）

- Source: 公開ノートブック「Mega Lucario ex V2」。LB Score **796.4**（公式 Mega Lucario 770.4 より改善）。
- **デッキは公式 Mega Lucario と同一**。改善は **agent ロジック（main.py V2）** のみ＝ロジック改良だけで +26 取れることの実例。

### Key Ideas
- V2 は手続き型サンプルを **OOP に再設計**（`LucarioPolicy` クラス、~548行）。`_score_option` が OptionType ごとにスコア関数へ分岐。
- 追加要素: **攻撃プランニング** `_plan_attack`/`_base_attack_after_evolution`（進化後のダメージまで見て最善attackを選ぶ）、エネルギー対象スコア、**デッキアウト察知** `_low_deck`（残り≤8で挙動変更）、カード個別対応（特殊エネ LEGACY_ENERGY=12、Lillie名シナジー LILLIES_PEARL=1172、スタジアム LUMIOSE_CITY=1267、Mega Lucario の攻撃 MEGA_BRAVE=983、Lunatone 特性記憶）。
- **検証済みローカルマッチアップ（各100戦, 先攻後攻入替）**:
  - V2 vs 公式V1: **70.7%**（70-29-1）/ avg_steps 137.7
  - V2 vs official_random: **99%** / avg_steps 56.0
  - V2 vs public Dragapult: **91%**（91-9）/ avg_steps 130.1
- 提出パッケージング改良版: `__pycache__`/`.pyc` 除外、必須ファイル `{main.py, deck.csv, cg/api.py, cg/libcg.so}` を提出後に検証。

### Useful for This Competition
- **外部ベンチマーク値**として有用: 強いルールベース Lucario は Dragapult を 91%, random を 99% で圧倒。我々の gauntlet で「強さの天井」目安になる。avg_steps ~130-140 が拮抗試合の長さ。
- V2 のポリシー構造（OOP＋OptionType別スコア＋進化後ダメージ評価）は、**自前ルールベース agent の良い設計テンプレート**（公式手続き型より拡張しやすい）。
- ロジックだけで 770→796 という事実は、デッキ固定でも agent 改良の価値が大きいことを示す。

### Risks / Caveats
- 公開コード＝全員が使える。これを超えるには探索/学習 or さらなるロジック改良が要る。
- 埋め込みマッチアップ表は作者の自己申告（こちらのハーネスで再現確認したい）。

### Experiment Candidates
- exp002: この V2 を含む公開/公式 agent をハーネスに載せ、マッチアップ表を**自前で再現**（91%/99% が出るか健全性確認）。
- 自前ルールベースは V2 の構造（進化後ダメージ評価・デッキアウト察知）を取り込んで設計する。

## 2026-06-17: Lucario v2 Strategic Baseline（public, raw: `references/raw/public_notebooks/`）

- Source: 公開「Pokemon TCG Lucario v2 Strategic Baseline」。LB 表記なし＝Strategy 向けの構造化ベースライン＋EDA。
- デッキ(BASELINE_DECK)は **lucario_v2 と完全同一**。新デッキ・新スコアは無し。価値は技法・戦略フレーミング・EDA。

### Key Ideas
- **`normalize_selection(ranked, scores, select)`**: optional 文脈（discard/bench/ダメカン/サーチ結果）で
  **score≤0 の中立手を minCount に強制されない限り取らない**。「ソートして先頭 maxCount を返す」素朴実装が
  optional 文脈で自滅手を選ぶ問題への対策（要 policy が per-option スコアを返す）。安全性ラッパーの一段上。
- **メタ飽和の指摘**: 「公開ラダーは Lucario コピーで飽和 → 最安の差別化は contested でないアーキタイプ」。
- **prize liability（KO時に相手が取るサイド数）比較**（デッキ選定指標）:
  Mega Lucario ex=**3**（Mega Evolution ex は3渡し、相手2KOで勝ち）/ Dragapult ex=2 だが Fezandipiti/Latias/Meowth ex も各2 で高 liability / Iono Bellibolt ex=2。
  → Lucario メタは高 liability。**低 liability（非ex/1-prize 主体）デッキは耐久面で有利**な可能性。
- 行動空間は可変・異種リスト＝固定ヘッド RL が不向き（indices 契約の妥当性を裏付け）。
- **belief modeling / belief-guided search を Phase-2** に置く＝我々の「determinization の相手モデルがボトルネック」知見(exp003/004/006)と一致。

### Useful for This Competition
- `normalize_selection` の「中立 optional 手を避ける」を安全性ラッパーに取り込む（取りこぼし減＝安定性）。
- **デッキ選定に prize liability を評価軸として導入**（exp007）。Lucario(3渡し)は強いが脆い → 低 liability 案を比較。
- Strategy レポートの裏付け: 行動空間 EDA・belief modeling 必要性は我々の独自性（相手モデルボトルネック）と整合。

### Risks / Caveats
- 中身は公式/公開 Lucario と同デッキ＝強さの上積みは無い（構造化と EDA が主）。
- normalize_selection は policy が per-option score を出す前提。lucario_v2 の `choose()` は最終選択のみ返すため流用には改修要。

### Experiment Candidates
- exp007(デッキ): prize liability を指標に Lucario vs 低liability案を fast harness で A/B。
- 安全性ラッパー v2: optional 文脈で中立手を避ける（normalize_selection 相当）を組込み、ミラー/対プールで取りこぼし減を確認。

## 2026-06-18: Pokemon AI Battle Agent: Mega Lucario（public, LB 906.9）

- Source: 公開「Advanced Heuristic Planning Agent」。LB 906.9 / Bronze。raw: `references/raw/public_notebooks/`。
- デッキ＝lucario_v2 と完全同一。LucarioPolicy（OO, bench進化/low-deck保護/stadium対策）＝公開V2系。
- **「40手 forward search」を謳うが実は壊れている**: `search_begin(sbi)`（入力1個のみ）＝正しい署名
  `search_begin(obs, your_deck, your_prize, opp_deck, opp_prize, opp_hand, opp_active)` と不一致で必ず例外→
  毎回 LucarioPolicy にフォールバック。戻り値も `res.state/res.error` を誤想定。**探索は実質無効**。
- 実態 = LucarioPolicy + クラッシュ安全（LB-860 と同系）。**我々の v001=915.2 が上回る**。新技術なし。

### 競争情報（重要）
- **公開の「advanced」notebook（LB-860, LB-906.9）はいずれも Search API を正しく呼べておらず**、黙って
  ルールベースに退化している。**Search API を実際に動かし相手モデル(belief接地)まで解いたのは我々だけ**
  （exp003/008, v002）。Strategy レポートの独自性を強く裏付ける。
- 教訓: 公開の高スコアは「強い探索」ではなく「強いルールベース+安定性」が源泉。ラダー上位＝安定性ゲーム。
