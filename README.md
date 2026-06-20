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

## 進捗（2026-06-20 時点）

ローカル評価は固定相手プールへの平均勝率。**メタは三すくみで一周し、頂点 = 非ex アタッカー**と特定。
**現状の eligible = {v006 非ex apex, v004 Crustle 壁}**（トップ #4 charmq の非exデッキを複製した v006 が主力）。

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
| exp007 | **メタ対策**（リプレイ解析） | **v003 anti-Crustle**（旧主力, 一時 LB 1123） |
| exp009 | 専用 Crustle 制御方策 | v005（制御は事故率・ミラーが課題） |
| exp010 | **RL 再挑戦**（Phase2 メタ討伐 / Phase3 ミラー特化） | **3重検証の誠実なネガティブ**（value 品質がボトルネック, 探索増で悪化）。打ち切り |
| exp011 | **メタ監視**（週次リプレイ解析・上位辿り） | メタの一周を特定／三すくみ＆apex=非ex を実証 |
| exp012 | **非ex apex 複製**（charmq #4 のデッキ） | **v006**（ex 0.667・Crustle 0.833・v003 0.600 を食う） |

### 提出（eligible = 最新2提出, 2026-06-20）
| 版 | 中身 | 状態 |
|---|---|---|
| **v006** | **非ex アタッカー apex**（charmq #4 複製） | PENDING（収束待ち, ローカルで ex+Crustle 両取り） |
| v004 | Crustle anti-ex 壁 | 864.9（実勝率0.59=収束途中。v006 の dragapult 弱点をカバー） |
| v003 | anti-Crustle（旧主力） | 旧 1100.8（eligible から押し出し） |

### 中心的発見
- **メタは三すくみで一周する**: ex ビート → Crustle anti-ex 壁 → **非ex アタッカー** → ex ビート。
  06-18 は Crustle 一色 → 06-20 は Lucario-ex 復権。**頂点は非ex**（単サイドで ex にレース勝ち＋Crustle の ex限定 Safeguard を貫通）。
- **リプレイ駆動のメタ分析が最重要レバー**: 自分の対戦＋上位プレイヤーの試合を解析し、トップ構築を複製して提出。
- **相手モデル(determinization)が探索の価値を決める**（exp008, 対照実験で実証）。
- **学習系は3重検証の誠実なネガティブ**（exp010）: warm-start belief-MCTS は強い rule-based を超えず、
  探索を増やすほど悪化＝value ネット品質がボトルネック。価値は「学習」でなく「推論時の探索＋belief」。
- **汎用方策が異種デッキを操縦できる**: Crustle(v004)・非ex(v006) を専用方策なしで運用可能。
- 詳細な提出戦略は [`competition/submission_plan.md`](competition/submission_plan.md)、レポート草稿は [`competition/report_draft.md`](competition/report_draft.md)。
- ⚠️ ラダーは「最新2提出のみ最終評価」。最良ペアを最新枠に維持すること。

### 週次メタ監視 / デッキ複製
```bash
cd workspace/exp011_meta_watch
uv run python analyze.py <our_submission_id>     # 自分の対戦のメタ分布
uv run python top_meta.py <top_player_sub_id>    # 上位プレイヤーの構築と戦績
uv run python extract_deck.py <sub_id> [out.json] # 任意選手の正確な60枚を複製（/extract-deck スキル）
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
