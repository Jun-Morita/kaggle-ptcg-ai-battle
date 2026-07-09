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

## 進捗（2026-07-09/10 時点）

**eligible = {v015-fix4 (RLプローブ), diag-probe (v014クローン)}**。v014自体はハーネス上の
出荷最良版（crustle 0.765→0.905 +0.14 のターン全体プランナー）のまま健在——ラダー枠は
RLフィードバック収集のため一時的にRL版へ切り替え中。

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
