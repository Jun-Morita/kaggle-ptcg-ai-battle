# スカウティング: Yushin Ito (sub 53955703, LB #7 1097.2, 2026-07-08)

同一アーキタイプ(Hop's Trevenant/non_ex_attackers)、n=1000戦のビッグサンプル。
我々の2大出血源にピンポイントで刺さる比較対象:

| マッチアップ | Yushin | 我々(v014) |
|---|---:|---:|
| dragapult | 0.48 (n=31) | 0.17-0.19 |
| mirror(non_ex_attackers) | 0.77 (n=261) | 0.585 |
| lucario_ex | 0.90 (n=49) | 0.77 |
| crustle_control | 0.84 (n=19) | 0.905 (我々の方が良い) |
| mixed_ex4 | 0.25 (n=206) | (要マッピング確認) |

## 行動分析 (analyze_adaptation.py + policy_diff2.py, revenge_policy REVENGE_BONUS=50 基準)
- 一致率は全マッチアップで一様に低い(0.24-0.29) = アーキタイプ切替でなく全体スタイルギャップ。
- dragapult戦のavg_bench=3.14(crustle同水準)、他の攻撃系マッチアップ(mixed_ex3/5, ex_beatdown)は2.45-2.56。
  展開の重さがテンポ負けに繋がっている可能性。

## TO_HAND サーチ優先度（最有力の具体的仮説、n=200試合分）
| カード | Yushin | 我々 |
|---|---:|---:|
| Lillie's Determination | 88 | **15** |
| Mist Energy | 88 | **43** |
| Hop's Choice Band | 112 | **367** |
| Boss's Orders | 78 | **283** |

我々はChoice Band/Boss's Orders(火力・妨害)を過剰取得し、Lillie's Determination(ドロー)/
Mist Energyを手薄にしている。リソース枯渇→テンポ低下の仮説はdragapult戦の速度負けと整合的。

## SETUP_BENCH_POKEMON / TO_BENCH: 一致率0-5%
セットアップ時に彼らはベンチをほぼ埋めない(their=[])。exp042の教訓
(「行動一致率の改善≠強さの改善」)により、この差分だけでパッチ化はしない。

## 次アクション候補（未着手、ft1完了後 or 手が空いたタイミングで）
TO_HANDサーチ優先度パッチ(Lillie's Determination/Mist Energyの優先度を上げ、
Choice Band/Boss's Ordersを下げる)を作り、**exp042と同じn≥200×5field評価で強さ検証**
してから判断する。行動差分だけで出荷判断はしない。
