# Submissions

| Version | Date | Source experiment | CV (local) | LB | File / notebook | References | Notes |
|---|---|---|---:|---:|---|---|---|
| v001 | 2026-06-17 | exp005_submit | 対プール~0.59-0.68 / vs random 1.00 / mirror 0エラー(40g) | **915.2** (ref 53775026, COMPLETE) | submit/v001_exp005_lucario_v2_safe/submission.tar.gz | exp002 lucario_v2 / 公開 LB-860 安全性パターン | lucario_v2 ヒューリスティック + クラッシュ安全ラッパー。**現状ベスト**。公開最高LB-860超え |
| v002 | 2026-06-17 | exp008_belief | 同一相手 PIMC 0.583 > 教師 0.528（dragapult 0.75/v1 0.583/mirror 0.42）/ mirror 0エラー / max_move 23s | **850.5** (ref 53780586, COMPLETE) | submit/v002_exp008_belief_pimc/submission.tar.gz | exp008 belief PIMC / exp002 lucario_v2 | belief PIMC + Conservative Override(margin0.10)。**v001(915)を下回る**。理由: ラダーは Lucario 飽和=ミラー支配的で PIMC の非ミラー優位が活きず、確率的ブレ＋低速で微減。**教訓: ローカル非ミラー改善≠ミラー飽和ラダー改善** |

`SUBMISSIONS.md` は人間向けの要約です。比較や再現に使う機械可読ログは `submit/submissions.csv` に残します。

## Rules

- 提出物は `submit/vNNN_expNNN_name/` に作る。
- 元実験、fold、モデル、推論設定、CV/LB を必ず記録する。
- 外部知識、外部データ、public notebook を使った場合は出典を記録する。
- 提出前に `scripts/validate_submission.py` で行数、列名、欠損、値域、ID の順序を確認する。
- 提出後に `scripts/record_submission.py` で `submit/submissions.csv` に追記する。
- 実アップロードはユーザー承認後に行う。
