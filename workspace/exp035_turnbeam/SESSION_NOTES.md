# exp035 — turn-beam（ターン全系列探索・検証付き上書き）→ 単体で v013 超え

## 動機
exp022 take-when-legal（差は per-decision でなくターン内スループット）＋ exp034 レース算術
（+30 と revenge 窓の同時成立が必要）→ pilot に欠けるのは「ターン全体の順序付け」。

## 設計の変遷（重要）
1. 初版: プラン算術スコアで常時上書き → **0.30 大退行**（exp003 の再現: 手書き評価 < チューニング済み heuristic）。
2. 検証付き（プライズのみ）: 無害だが発火 0.15/試合 ≈ 不発（base は同一ターンのプライズを取りこぼさない）。
3. **状態汚染バグ**: 探索内 rollout で実対局用 base インスタンスを呼び lucario_v2 のグローバル
   (`plan`/`_rev`) が汚染 → paired 0.34。**別インスタンス分離で解決**（恒久教訓）。
4. 最終形: **プライズ優先＋ダメージ(≥+30)辞書式、全 K determinization で base 系列を確実に
   上回る初手のみ採用**。beam=5/branch=10/K=2, 方策呼び出し不要の engine fork 展開, ~1s/試合。

## 結果（n=200/系列, 全て 0err, 発火 ~2.3/試合）
| matchup | 基準v012 | v013(guard) | turn-beam単体 |
|---|---|---|---|
| ex_lucario | 0.77 | **0.860** | 0.770 |
| dragapult | 0.155 | 0.205 | **0.220** |
| archaludon | 0.175 | 0.165 | **0.195** |
| mirror_chq | 0.585 | 0.555 | 0.580 |
| crustle | 0.765 | 0.795 | **0.905 (+0.14, ~4SE)** |
| 合計 | 2.45 | 2.58 | **2.67** |
| paired vs v012 | — | 0.515 | 0.530 |

## 解釈
- **系列効率は「壁を削る」マッチで最大**（crustle +0.14）: 毎ターンの与ダメ最大化系列＝Band/進化/
  スタジアムの順序が長期戦で複利。床マッチ（dragapult/archaludon）も +0.02〜0.065 浮上。
- guard(対ビートダウン ex +0.09) と**効く場所が直交** → 合成が v014 本命（単純加算 ~2.76）。
- 検証付き上書き（全K・base比較・上振れ限定）は3連続で機能する設計原理として確立
  （v013 doom / exp019 lethal / exp035 throughput）。

## 資産
- `turnbeam_policy.py`（TB_K/TB_BEAM/TB_BRANCH/TB_MAXSTEPS）/ `eval_tb.py` / `run_chain.sh`
