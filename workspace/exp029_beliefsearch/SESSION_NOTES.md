# exp029 — belief-search v2（メダル圏復帰のための高度 piloting）

計画（2026-07-02 ユーザー合意）: Stage 0 時間予算実測 → Stage 1 相手応手ガード(2-ply safety)
→ Stage 2 選択的 belief-PIMC（exp008 の完成）。検証は n≥200 paired・全マッチ無退行・0 crash。

## Stage 0 — 時間予算の実測（完了）

### 公式のタイム制約（replay configuration + kaggle-environments cabt.json）
- `actTimeout = 0`（per-move 制限なし）
- `runTimeout = 2000s`（エピソード全体）
- **`remainingOverageTime = 600s` = エージェント毎の累積持ち時間プール**。
  actTimeout=0 なので全思考時間がここから減る。6/30 環境更新でプール切れ＝タイムアウト負け。

### 決定回数（top_debauchery_grim 120 リプレイ実測）
- steps/episode: mean 171 / p90 230 / max 271
- **decisions/agent/game: mean 85 / p90 123 / max 164**

### 探索プリミティブの実測コスト（bench_search.py, 実ゲーム中 40 サンプル, 現実的 determinization）
- `search_begin` ~0.4ms, `search_step` ~0.2ms
- 自ターン残りロールアウト ~1ms、**相手ターン丸ごとロールアウト ~4ms（平均 7.8 手）**
- **ガード1単位（begin＋自ターン仕上げ＋相手ターン）≈ 5ms → K=5 で ~0.03s/決定**

### 予算の結論
- 全決定（~85回）を K=5 でガードしても **~2.5s/試合 = 持ち時間の 0.4%**。桁で余裕。
- 選択的 full-PIMC（24 options × K=3-5 × 長ロールアウト）でも数百 s に収まる設計が可能。
- Kaggle 実機がローカルより 2-5 倍遅くても問題なし。exp008 当時の「30s/move」は
  当時の実装オーバーヘッドであり、エンジンの本質コストではない（今回 sub-ms/step を確認）。
- 注意: プレースホルダ determinization（全エネ/Snorlax）はロールアウトが ~3 手で終わり
  コストもゲーム性も過小になる。ベンチ・本番とも実デッキサンプルを使うこと。

**GO for Stage 1**（時間は制約にならない）。

## 資産
- `bench_search.py` — 実ゲーム内で search primitives を計測（再利用可）。

## Stage 1 — 相手応手ガード（guard_policy.py）結果 → GO

設計: v012（v_trev＋revenge RB=50）の MAIN 単一選択に限り、base の選択を K=4 の belief
determinization で「自ターン仕上げ→相手ターン丸ごとロールアウト」し、全 K で破滅
（敗北 / 2プライズ献上 / 充電済み主力の消失）のときだけ、破滅を全 K で回避できる代替に上書き。
belief: 相手の隠れ札は相手の公開札（盤面+トラッシュ）からサンプル、自山は残リスト（prize-blind）。

### n=200 結果（基準 = exp027 v_trev sweep）
| matchup | v_trev基準 | guard | Δ |
|---|---|---|---|
| ex_lucario | 0.77 | **0.860** | **+0.09 (~2.6SE 有意)** |
| dragapult | 0.155 | 0.205 | +0.05 |
| archaludon | 0.175 | 0.165 | −0.01 |
| mirror_chq | 0.585 | 0.555 | −0.03 (~0.9SE, ノイズ内) |
| crustle | 0.765 | 0.795 | +0.03 |
| paired vs 素v012 | — | 0.515 | 中立 |

- 全マッチ 0 crash、0.4-1.8s/試合（持ち時間600sの<1%）。発火 0.6-3回/試合。
- **判定 GO**: 有意退行なし＋最大票田 ex_lucario で有意改善。「実在機構（相手の攻撃）を
  方策が無視していた」クラス＝gust 修正と同じ転移クラス、という事前根拠とも整合。
- 学び: exp015(greedy終盤探索が計画破壊)との差 = ガードは「全K破滅時のみ上書き」の
  拒否権設計で、base の多ターン計画を通常時は壊さない。

### 実行時の教訓
- `nohup` でも Claude セッション終了で死ぬ → **setsid + PID 監視**が正解。
- `pgrep -f` は監視コマンド自身にマッチする（偽 ALIVE）→ PID を直接持つ。
- WSL 再起動（23:45）で一度全滅した。長時間走行は分割・追記型が安全。

## v013 提出（完了, ユーザー承認済 2026-07-02 15:28 UTC）
- `guard_patch.py`（PATCH_SRC = revenge(RB=50) + guard 自己完結ソース, GUARD_K=4 焼き込み）
- build: tar 構造 OK / smoke 0err / **ビルド版でガード発火確認**（12回/20試合, vs ex 16-4, 内部エラー0）
- 記録: submissions.csv / SUBMISSIONS.md 済。**eligible={v013, v012}**（v011 814.9 押し出し）。
- 判定条件: v013 が v012(~815) を有意に超えるか（μ600 から要収束, 48試合/日）。
- 超えたら **Stage 2**: 高レバレッジ局面限定の belief-PIMC（fine_classify でアーキタイプ推定 belief）。
