# Kaggle Agent Template

このリポジトリは、Claude Code で Kaggle 実験を進めるための軽量テンプレートです。

## まず読む

作業開始時は次を確認する。

1. `competition/overview.md`
2. `references/knowledge/INDEX.md`
3. 最新の `daily_reports/*.md`
4. GPU 利用可否が未確認なら `uv run python scripts/check_gpu.py`
5. `git status --short`

コンペ仕様、評価指標、提出形式、fold 方針が曖昧なまま学習コードを書かない。

## このコンペ固有（PTCG AI Battle）— 以降の汎用ガードより優先

このテンプレは汎用の CV/CSV コンペ向け。本コンペは**エージェント提出＋ライブ・ラダー**型なので、
以降の「fold / metric / CSV 検証」系ガードは下記に**読み替え／無効化**する。

- 形式: **エージェント提出（tar.gz: `main.py` を top-level＋`deck.csv`＋`cg/`）＋ライブ TrueSkill ラダー**。
  CSV提出・fold・オフライン metric は**無い**。Simulation と Strategy(レポート, $240k)を一体で進める（素材は `competition/report_*.md`）。
- 概念の読み替え:
  - 「CV」= ローカル harness(exp001) の**対メタプール勝率**（先後入替, 例外=反則負け）。
  - 「LB」= ラダーレート（μ0=600, 勝敗のみ, **最新2提出で最終評価**, ライブ継続, ~10分/試合）。
    新規提出は μ600 から**収束途中**＝早期スコアを過小評価しない。
  - 「metric/validate」= tar構造＋deck=60枚＋**クラッシュ安全スモーク0エラー**（`scripts/build_submission.py`）。
    `metrics.py`/`tests`/`validate_submission.py`/`sample_submission.csv` は本コンペでは使わない。
  - 「CVとLBがずれたら」= fold でなく **メタプール≠ラダーメタ / μ600収束 / ミラー飽和**を疑う。
- 必須: 提出エージェントは**クラッシュ安全**（例外・不正手→合法フォールバック）。高速手番でタイムアウト回避。
- メタは**動的に回転**する。**リプレイ駆動のメタ監視**が最重要レバー。週次ループ:
  `/meta-watch`（回転検知）→ 変化あれば `/extract-deck`（上位デッキ複製）→ `/build-submit`（ビルド・スモーク・承認後提出）。
- 提出後は `submit/SUBMISSIONS.md` ＋ `submit/submissions.csv` に記録。eligible は最新2なので枠管理に注意。
- 学習/探索の**負の結果も誠実に記録**（SESSION_NOTES）。再現性は Strategy レポートの評価軸。

## 実装前ガード

`competition/overview.md` の次の項目が空なら、学習コードや提出コードを書かない。まず不足情報を埋める。

- Metric の公式定義とローカル実装方針
- Submission の type、required file、required columns
- Validation の fold method、grouping key、leakage risks
- Rules の external data、pretrained models、internet

## 実行可能なガード

- metric を実装・変更したら `src/kaggle_agent_template/metrics.py` と `tests/` を更新し、`uv run pytest` を実行する。（CV/CSVコンペ向け。本コンペは「このコンペ固有」参照＝metric なし）
- 提出CSVを作ったら `scripts/validate_submission.py` で `sample_submission.csv` と突き合わせる。（CSVコンペ向け。本コンペは tar構造＋クラッシュ安全スモーク＝`scripts/build_submission.py`）
- 提出したら `submit/SUBMISSIONS.md` に人間向けの要約を書き、`submit/submissions.csv` に機械可読ログを残す。
- 実験実行時は seed を適用し、`results/run_metadata.json` に git SHA、config hash、主要ライブラリversionを残す。

## 環境とGPU

- Python 実行、lint、notebook 起動は `uv run` 経由を基本にする。
- `uv sync` 後は `src/kaggle_agent_template/` が editable install される。手動の `PYTHONPATH` 追加に依存しない。
- 環境構築後は `uv run python scripts/check_gpu.py` で GPU 利用可否を確認する。
- GPU が使える場合は、コンペのタスクに合う GPU 対応ライブラリを優先して検討する。
- PyTorch などの重い GPU 依存は、コンペで必要になってから追加する。
- 導入コマンドは、対象ライブラリの公式ドキュメントに基づいて提案する。
- Kaggle Notebook で実行する場合は、accelerator、internet、external data、pretrained model のルールを確認する。

## 進め方

1. `competition/overview.md` にコンペ情報を整理する。
2. notebook、discussion、外部記事から使う知識を `references/knowledge/` に要約し、`INDEX.md` を更新する。
3. `workspace/expNNN_name/` に実験ディレクトリを作る。
4. 実験ごとに `SESSION_NOTES.md` へ仮説、変更、結果、出典を書く。
5. その日の判断と次アクションを `daily_reports/YYYYMMDD.md` に集約する。
6. 提出したら `submit/SUBMISSIONS.md` に CV / LB / 出典を残す。

## 外部知識の扱い

- Kaggle notebook、discussion、外部記事を読んだら、使えそうな知識を `references/knowledge/` に md で残す。
- raw の HTML、ipynb、スクリーンショット、取得ファイルは `references/raw/` に置く。raw は Git に入れない。
- md には URL、取得日、作者、対象コンペ、要点、使える場面、リスク、実験候補を書く。
- 重要な知識を追加したら `references/knowledge/INDEX.md` も更新する。
- 内容をそのまま長く貼らない。要約し、出典を明記する。
- notebook や discussion 由来のアイデアを実験に使う場合は、`SESSION_NOTES.md` に出典を書く。
- 提出に効いた外部知識は `submit/SUBMISSIONS.md` にも出典を残す。
- rules の external data、pretrained models、internet が不明な場合は、外部データや外部モデルを使うコードを書かない。

## 実験ルール

- 1 実験 1 ディレクトリで管理する。1 notebook だけで完結させない。
- 1 実験 1 仮説を基本にする。
- notebook は EDA や試行錯誤に使う。再実行したい学習・推論は `.py` に移す。
- 実験ディレクトリには `SESSION_NOTES.md`, `config.yaml`, `run.sh`, `train.py` を置く。
- 同じコードでパラメータだけを変える場合は、同じ実験ディレクトリ内の `configs/*.yaml` に分ける。大きく方針が変わる場合だけ新しい実験ディレクトリを作る。
- seed、fold、metric、主要パラメータは config に置く。
- seed は `kaggle_agent_template.repro.set_seed()` で適用する。
- 実験時は `results/run_metadata.json` に git SHA と config hash を残す。
- （以下の fold/metric 行は CV/CSV コンペ向け。本コンペは「このコンペ固有」参照＝fold なし、metric は harness 勝率）
- fold はデータ単位を確認してから決める。group や時系列がある場合はランダム KFold にしない。
- fold を作ったら `workspace/folds/` に保存し、使った version を `SESSION_NOTES.md` と config に記録する。
- 前処理の fit は train fold のみで行う。
- metric 実装は、小さい手計算ケースや公開 baseline と照合してから実験に使う。
- CV と LB がずれたら、モデルより先に fold と metric 実装を疑う（本コンペは メタプール≠ラダーメタ / μ600収束 を疑う）。
- データ、モデル、提出物などの大容量ファイルは Git に入れない。

## MCP は任意拡張

MCP は最初から必須にしない。データ理解や notebook 生成を繰り返す段階で必要になったら追加する。

追加する場合は、次の3種類に分ける。

- `data_information`: `competition/overview.md` や軽量なデータ要約を返す。コンペ固有の列説明、join key、target、metric を扱う。
- `analysis_executor`: 小さな分析関数を実行し、結果を `workspace/expNNN_name/results/artifacts/` に保存して path を返す。
- `notebook_writer`: 実験ディレクトリ内の notebook に markdown/code セルを追加する。ただし再利用する処理は `.py` に移す。

MCP の分析結果は、返された artifact を必ず読んでから考察する。コード生成だけで判断しない。

## 提出前チェック

> 本コンペ（エージェント提出）は「このコンペ固有」セクションを優先。実体は `/build-submit`（`scripts/build_submission.py`）:
> tar構造（`main.py` top-level＋`deck.csv`＋`cg/`）＋deck=60枚＋**クラッシュ安全スモーク0エラー**＋eligible=最新2 を確認。
> 以下の CSV 行は CV/CSV コンペ向け。

- 行数、列名、ID 順序、欠損、値域を確認する。（CSVコンペ向け）
- `uv run python scripts/validate_submission.py --sample data/raw/sample_submission.csv --submission submit/vNNN_expNNN_name/submission.csv` を実行する。（CSVコンペ向け）
- 提出元の実験、fold、モデル、CV、推論設定を記録する。
- `uv run python scripts/record_submission.py ...` で `submit/submissions.csv` に追記する。
- CSV 提出は `templates/submit_csv/`、Kaggle kernel 提出は `templates/submit_kernel/` を必要に応じてコピーして使う。
- Kaggle への実提出はユーザー承認後に行う。

## Claude Code の振る舞い

- 既存ファイルを読んでから作業する。
- 不明点は仮説を添えて短く確認する。
- 大きな変更では短い方針を出してから実装する。
- 実装後は実行可能な検証を行う。
- 検証できない場合は、理由とリスクを記録する。
- 作業の区切りでは commit を提案する。ただし `git commit` はユーザーが実行する。提案時は staging 対象と commit message 案を示す。
