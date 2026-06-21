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

## 進捗（2026-06-21 時点）

ローカル評価は固定相手プールへの平均勝率。**メタは三すくみで一周し、上位は単サイド非ex に収束**。
**現状の eligible = {v008 deck-dispatch, v007 専用非ex}**（LB ~1080, competitive 圏）。
**方策はヒューリスティックの上限に到達**（v008/RL/意思決定diff の3方向で一致）。

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

### 提出（eligible = 最新2提出, 2026-06-21）
| 版 | 中身 | 状態 |
|---|---|---|
| **v008** | **deck-dispatch 方策**（charmq非ex, サーチ安定化） | PENDING（vs ex0.80/Crustle0.767/mirror0.56） |
| **v007** | 専用非ex方策（ミラー強化） | 1079（収束水準） |
| v006 | 非ex apex（汎用方策） | eligible 外（ミラー0.31 で負債） |

### 中心的発見
- **メタは三すくみで一周し、収束する**: ex ビート → Crustle 壁 → **単サイド非ex** → …。06-18 Crustle 一色 → 06-20 ex 復権 →
  上位は**単サイド非ex に収束**（Hop's Trevenant / Alakazam。単サイドで ex にレース勝ち＋Safeguard 貫通）。
- **リプレイ駆動のメタ分析が最重要レバー**: 自分＋上位の試合を解析し、回転に追従して提出（v003→v004→v006→v007→v008）。
- **デッキ⊗方策は密結合**: #1 のリストを複製しても我々の方策では回らない(ex 0.167)。我々が回せる charmq デッキが現実解。
  汎用方策＋的を絞ったパッチ（攻撃モデル/サーチ優先度）で v003→v008 と改善。
- **方策はヒューリスティック上限に到達**（3方向で一致）: ①RL 3重ネガティブ ②v008 後のミラー微調整が無効 ③意思決定 diff で
  上位の選択を模倣しても勝率不変（ミラーは対称~0.5、乖離選択の多くは等価に good）。**価値は学習でなく推論時の探索＋相手モデル**。
- **相手モデル(determinization)が探索の価値を決める**（exp008, 対照実験）。
- 上限超えの唯一の筋＝**深層強化学習**（ただし素朴 self-play は不可。stock-vs-stock で value 較正→MCTS が未試行ルート）。
- レポート: 草稿 [`competition/report_draft.md`](competition/report_draft.md) / 数値台帳 [`competition/report_evidence.md`](competition/report_evidence.md) / 戦略リファレンス [`references/knowledge/ptcg_strategy.md`](references/knowledge/ptcg_strategy.md)。
- ⚠️ ラダーは「最新2提出のみ最終評価」。最良ペアを最新枠に維持すること。

### 週次運用（スキル化済み）
```bash
/meta-watch                # 最新提出のメタ分布＋回転検知＋LB（exp011 meta_watch.py）
/extract-deck <sub_id>     # 任意選手の正確な60枚を複製（exp011 extract_deck.py）
/build-submit              # デッキ+方策→ビルド→実物スモーク→承認後提出（scripts/build_submission.py）
# 上位スカウト: workspace/exp011_meta_watch/top_meta.py / 意思決定diff: exp013_router/policy_diff.py
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
