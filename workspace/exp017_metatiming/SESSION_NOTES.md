# exp017_metatiming — SESSION NOTES

仮説: 2026-06-22 のメタ回転（フィールドが単サイド ~54% に収束、ex 26%・Crustle 7% に縮小）で、
spread カウンター(Dragapult)の期待勝率が v008(非ex)を上回るタイミングが来たか。

## 方法（`eval_metatiming.py`）
- meta-watch(sub 53898216)のシェアを我々のローカル相手に割付け、**重み付き期待フィールド勝率**を算出。
- 相手: non_ex=charmq(v008操縦) 0.34 / lucario_ex 0.28 / Alakazam 0.20 / crustle(generic=v004) 0.07 /
  abomasnow 0.07 / iono 0.05。テスト: Dragapult(baseline) vs v008(charmq)。先後入替, n=30/matchup, err 0。

## 結果（n=30）
| matchup | share | Dragapult | v008 |
|---|---|---|---|
| 非ex(charmq) | 34% | **0.867** | 0.467 |
| lucario_ex | 28% | 0.567 | 0.633 |
| Alakazam | 20% | 0.633 | 0.700 |
| crustle(v004) | 7% | **0.000** | 0.800 |
| abomasnow | 7% | 0.533 | 0.467 |
| iono | 5% | 0.467 | 0.633 |
| **重み付き期待勝率** | | **0.634** | **0.590** |

## 結論
- **Dragapult > v008（+0.044）＝現メタで spread が好機**。優位は全て最大スライスの非ex(0.867 vs 0.467)から。
- **実フィールド補正で差は拡大**: ローカル非ex=charmq(v008 ミラー0.467)だが、実ラダーの非exは我々を上回る(v008 実測 0.38)
  → v008 実期待は <0.59。spread は操縦に依らず非exを狩るので Dragapult は実の強い非exでも ~0.85 維持 → 実差 +0.08〜0.10。
- 唯一の致命的穴 = **Crustle 0.0**（現 7%, 縮小中）。abomasnow 0.53/iono 0.47 もやや弱いが小スライス。
- メタ・タイミングの賭け: 単サイド収束が続く間は Dragapult 有利。Crustle 再興 or ex 復権なら v008 有利に戻る。

## ★訂正（2026-06-22, 実物スモーク）: 上の exp017 結論は誤り＝Dragapult は提出しない
- `/build-submit` で Dragapult と v008 の**実物 artifact を同一スモークハーネス**で比較（n=16, 0エラー）:
  | 相手 | v008(charmq) | Dragapult |
  |---|---|---|
  | ex(lucario_v2) | **0.875** | **0.188** |
  | Crustle | **0.938** | **0.000** |
  | dragapult | 0.188 | 0.500 |
- **exp017 の「dragapult vs ex 0.567」は過大評価＝プロセス内 import 順の状態汚染**（AC＋baselines＋router を同一
  プロセスで混載すると同一マッチアップが 0.30〜0.55 と振れる）。クリーンな実物スモークでは **dragapult vs ex 0.188 / Crustle 0.000**。
- **実フィールド期待勝率（再計算）**: v008（実ラダー値: 非ex0.38/ex0.94/Alakazam0.67/Crustle0.75）≈ **0.64**
  ＞ Dragapult（非ex0.85/ex0.19/Crustle0.0）≈ **0.53**。
- **結論**: Dragapult は v008 への hard counter だが、**ex(28%)と Crustle(7%)で壊滅**し現フィールドで v008 に劣る。**提出しない**。
- **教訓**: ローカルの重み付き eval は**モジュール混載の状態汚染**で絶対値が信用できない。**実物 artifact スモーク（独立 exec）が信頼できるハーネス**。今後メタ評価は build_submission.py のスモーク方式で行う。
- 次: **v008 維持**（eligible {v008, v007}）。v008 唯一の弱点＝非exミラー（操縦は頭打ち exp013/015）。
  spread カウンターは「ex も Crustle も消える」局面まで保留。`/meta-watch` 継続。
