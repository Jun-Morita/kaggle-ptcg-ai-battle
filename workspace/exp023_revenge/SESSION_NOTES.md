# exp023 — real-strategy-informed piloting: the REVENGE-WINDOW mechanic (→ v011 submitted)

## 仮説
take-when-legal で「単一カード patch クラスは枯渇／合法手単位ではトップと一致」と結論したが、
それは *どのカードを出すか* の話。**攻撃の評価・対象選択**は未監査だった。実カード挙動を精読したところ、
我々の非ex pilot は **デッキの根幹機構を見落としていた**:

- **Hop's Trevenant「Horrifying Revenge」(attack idx0)**: 1エネ30。**ただし「前ターン(相手の番)に自軍 Hop's ポケが
  攻撃で KO された」なら +100＝130**。130 は大半の ex / 140-150 壁を割る。＝このデッキは**リベンジ・トレード型**
  （単サイドを1体差し出し→130 で殴り返す）。
- だが `router_policy._nonex_base_attack` は Revenge を **flat 30 + boost + cb でハードコード**（[router_policy.py:58]）。
  pilot は 130 の revenge-KO を**永遠に見えない**→ revenge 窓で対象/進化を最適化できない。

## 実装（`revenge_policy.py`, v010 gust 基盤に3定数を追加, env 注入でスイープ可）
1. **REVENGE_BONUS**（本命）: window 検出（**相手が前ターン以降サイドを取った＝自軍が KO された**, module-global `_rev` で
   ターン境界管理）時、Trevenant Revenge の planning ダメージに +BONUS。engine は実 +100 を適用するので、これは pilot の
   *選択* を直すだけ（130 を認識し revenge-KO を狙う／進化を急ぐ／正しい対象に Boss）。
2. **PRIZE_W**（prize trade）: gust の flat +500 を `500 + PRIZE_W*(prize-1)` に＝多サイド(ex)KO を優先。
3. **BACKUP_CHARGE**（継戦）: active 充電済みなら控えの Trevenant にエネを回す（トレード後すぐ revenge）。
- 既定 (0,0,0) = v010 完全一致（健全性: baseline ミラー vs v010 ≈ 0.50 を確認）。

## 評価（subprocess 隔離＝設定間の汚染ゼロ; リーグ = mirror vs v010 / ex / Crustle / dragapult）
n=60 走査 → 有望株を n=200 確認（SE≈0.035, この session の「小n はノイズ」教訓を遵守）:

| config | mirror | ex | Crustle | dragapult | field |
|---|---|---|---|---|---|
| BASELINE=v010 | 0.450 | 0.770 | 0.730 | 0.145 | 0.594 |
| **REVENGE_BONUS=50** | **0.505** | 0.755 | **0.780** | 0.140 | **0.609** |
| PRIZE_W=300 | 0.505 | 0.710 | 0.755 | 0.140 | 0.586 |
| REVENGE_BONUS=100 | 0.480 | 0.785 | 0.705 | 0.185 | 0.611 |
| RB=50 + PW=300 | 0.530 | 0.730 | 0.715 | 0.150 | 0.598 |
| BACKUP_CHARGE=1 (n60) | 0.383 | — | — | — | 退行 |

- **勝者 = REVENGE_BONUS=50**（PW=0, BC=0）: 弱点2マッチ（ミラー+0.055 / Crustle+0.05）を改善、ex/dragapult 退行なし、field 最良。
- **moderate(+50) > +100/+130**: window 検出は proxy（誤検出あり）。+50 は Revenge を 80 と見なす＝対象を動かすに十分だが
  「幻の130KO」に過剰コミットせず＝**誤検出に頑健**。良い設計知見。
- BACKUP_CHARGE / PRIZE_W≥600 は退行（discard）。

## 提出（v011, ユーザー承認済 2026-06-25）
- ビルド: `env REVENGE_BONUS=50 build_submission.py --deck charmq --policy lucario_v2 --patch revenge_policy.py`。
  built artifact smoke: ex 0.79 / Crustle 0.92 / dragapult 0.21, **0err crash-safe**, `dmg += 50` を main.py で確認。
- **eligible = {v011, v006}**（最新2 by time; v011 ⊃ v010 なので v010 を押し出し, v006 を単純アンカーとして温存）。
- **CV/LB 転移は要検証**（ローカル改善が転移しなかった前科4回）。ただし本件は **gust クラス**（実機構の見落とし修正,
  過学習でない）＝転移した唯一のクラス。ラダーが判定。

## 再利用資産
- `revenge_policy.py`（env 注入定数, gust 基盤）/ `eval_one.py`（リーグ評価, JSON 出力）/ `sweep.py`（subprocess 隔離 1次元スイープ）/ `sweep_results.json` / `build_v011/`。
- 手法: **実カード挙動 → 原理を定数化 → subprocess 隔離スイープ → n≥200 ロバストゲート → built-artifact smoke → 提出**。
