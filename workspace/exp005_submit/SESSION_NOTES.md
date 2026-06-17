# exp005_submit — SESSION NOTES

## 目的
最初の実提出ベースラインを用意する。最強ルールベース（exp002 lucario_v2, プール0.680）に
**クラッシュ安全ラッパー**を付与し、ラダーで例外＝敗北/Error を起こさない堅牢な提出物にする。

## 参考（公開 LB-860 notebook の知見）
- `references/raw/public_notebooks/strong-start-safe-agent-turn-search-lb-860.ipynb`。
- **LB 860 の正体 = 公式 Mega Lucario ヒューリスティック ＋ クラッシュ安全性**。
  search_plan は `search_begin(sbi)` という誤った呼び出し形で書かれ `USE_SEARCH=False` 既定 → 探索は未使用。
  つまり 796→860 の +64 はほぼ全て**安定性**（検証はミラー対戦なので例外回避が重要）。exp002/004 の知見と一致。
- 戦略レバー（notebook記載, 我々の分析と一致）: ①デッキ（最大効果）②Search 先読み ③上位リプレイ模倣/RL。

## 実装
- `build_submission.py`: exp002 の lucario_v2 policy を読み、`def agent(`→`def _base_agent(` にリネーム、
  末尾にクラッシュ安全 `agent()` を追記。
  - `agent()`: obs パース失敗 or 例外 or 不正選択 → `_legal_fallback`（先頭 minCount 個）。`_valid()` で
    範囲/重複/件数を検証。正常時は `_base_agent` の結果をそのまま返す（＝lucario_v2 と同一挙動）。
  - `deck.csv`（lucario_v2 デッキ）＋ `cg/`（ローカルエンジン, pycache除外）を同梱し、**main.py をトップ階層**に。
  - 構造検証: `{main.py, deck.csv, cg/api.py, cg/libcg.so}` 必須、cache無しを確認。
- `validate_local.py`: build/main.py を **player ごとに独立モジュール**でロード（policy がモジュールグローバル
  `pre_turn/ability_used/plan` を使うためミラーで共有不可）→ ミラー/対random/対プールを集計。

## 検証結果 (n=40/相手, swap, 2026-06-17)
- **ミラー: エラー 0/40**（reasons は prize-out 38 = クリーンな決着）→ Kaggle 検証(ミラー)通過見込み・例外で敗北しない。
- **vs random: 1.000 (40-0), エラー0** → 方策は機能。
- vs dragapult 0.700 / lucario_v1 0.550 / lucario_v2(mirror) 0.525 → 素の lucario_v2 と同等（ラッパーは正常時無変化）。
- 判定: mirror crash-free=PASS, beats random=PASS, 強さ維持=OK。

## 提出物
- `build/submission.tar.gz`（main.py + deck.csv + cg/, 8ファイル）。`submit/v001_exp005_lucario_v2_safe/` にコピー。
- いずれも Git 管理外（3rd-party policy + 競技 cg/ を含むため）。

## 提出手順（ユーザー承認後）
```
kaggle competitions submit -c pokemon-tcg-ai-battle \
  -f workspace/exp005_submit/build/submission.tar.gz \
  -m "v001 lucario_v2 + crash-safety"
```
- 5提出/日・最新2つのみ採点・μ0=600。提出後に LB レートを `submit/SUBMISSIONS.md`/`submissions.csv` に記録し、
  ローカル勝率との校正点にする。

## 次アクション
- 提出して LB 校正点を取得（lucario_v2+安全性 が公開 860 に対しどこに着地するか）。
- Lever 1（デッキ）: A/B で deck.csv を 200+戦比較し改良（最大効果）。
- exp005b: search を**正しい API 形**（exp003 で検証済）で安全に有効化し、自己対戦で勝率向上を確認できたら採用。
- 本命 exp006(BC/IL): 上位リプレイ/強ルールベース log で warm-start。

## 出典
- 公開 LB-860 notebook（安全性パターン）/ exp002（base policy・バー）/ exp003（正しい Search API 形）。
