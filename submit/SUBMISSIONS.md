# Submissions

| Version | Date | Source experiment | CV (local) | LB | File / notebook | References | Notes |
|---|---|---|---:|---:|---|---|---|
| v001 | 2026-06-17 | exp005_submit | 対プール~0.59-0.68 / vs random 1.00 / mirror 0エラー(40g) | _PENDING (ref 53775026)_ | submit/v001_exp005_lucario_v2_safe/submission.tar.gz | exp002 lucario_v2 / 公開 LB-860 安全性パターン | lucario_v2 ヒューリスティック + クラッシュ安全ラッパー。Simulation track。提出済 2026-06-17、ラダー集計待ち |

`SUBMISSIONS.md` は人間向けの要約です。比較や再現に使う機械可読ログは `submit/submissions.csv` に残します。

## Rules

- 提出物は `submit/vNNN_expNNN_name/` に作る。
- 元実験、fold、モデル、推論設定、CV/LB を必ず記録する。
- 外部知識、外部データ、public notebook を使った場合は出典を記録する。
- 提出前に `scripts/validate_submission.py` で行数、列名、欠損、値域、ID の順序を確認する。
- 提出後に `scripts/record_submission.py` で `submit/submissions.csv` に追記する。
- 実アップロードはユーザー承認後に行う。
