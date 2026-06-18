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

## 進捗（2026-06-18 時点）

ローカル評価は固定相手プールへの平均勝率。**現状の主力 = v003 anti-Crustle（LB 1088.3, 公開最高909超え）**。

### 実験
| 実験 | 内容 | 結果 |
|---|---|---|
| exp001 | ローカル対戦ハーネス | 完了（~10ms/game, 先後入替, 例外=反則負け） |
| exp002 | ルールベース5種＋random 総当たり | 強さ序列確定（lucario_v2 0.680 がプール最強） |
| exp003 | Search API 1手読み（素朴） | 0.21–0.27（探索は placeholder 相手で有害） |
| exp004 | AlphaZero 自己対戦(GPU) | ~0.03（デモ規模では非競争的） |
| exp005 | クラッシュ安全提出 | **v001**（LB 841.8） |
| exp006 | 模倣学習(BC) | 0.389（データでスケール、教師未達） |
| exp008 | belief 探索(PIMC) | belief 0.417 vs placeholder 0.083（5倍）。探索の価値は相手モデル次第 |
| exp007 | **メタ対策**（リプレイ解析） | **v003 anti-Crustle 提出** |
| exp009 | 専用 Crustle 制御方策 | v005（制御は事故率・ミラーが課題） |

### 提出（LB, 2026-06-18）
| 版 | 中身 | LB |
|---|---|---|
| **v003** | **anti-Crustle カウンター** | **1088.3** 🏆 |
| v001 | Lucario + 安全性 | 841.8 |
| v002 | belief PIMC | 820.1 |
| v004 | Crustle 模倣(汎用) | 742.9 |
| v005 | Crustle 制御(専用) | 600.0（収束中） |

### 中心的発見
- **メタ = Crustle anti-ex 壁コントロール**（実ポケカ Safeguard control）。全-ex デッキ(Lucario)は構造的に negate される。
  リプレイ解析で特定し、**1点修正の anti-Crustle 方策(v003)で counter → LB 1088.3**。
- **相手モデル(determinization)が探索の価値を決める**（exp008, 対照実験で実証）。
- 公開勢は全員 Mega Lucario + 安全性で Crustle 未対応・探索も誤用 → **メタ対策と動く探索で我々が先行**。
- 詳細な提出戦略は [`competition/submission_plan.md`](competition/submission_plan.md)。
- ⚠️ ラダーは「最新2提出のみ最終評価」。最良(v003)を最新枠に維持すること。

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
