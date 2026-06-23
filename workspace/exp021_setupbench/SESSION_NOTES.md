# exp021_setupbench — SESSION NOTES

仮説: 公式 disc708586「セットアップのベンチは任意（minCount==0→部分集合可）」より、
我々の pilot が **SETUP_BENCH_POKEMON を未スコア化→全 basic を並べる**のは prize-liability の漏れ。
v009 規律(MAIN のみ)を**セットアップ並べにも拡張**すれば、苦手なミラー(0.40)を改善できるはず。

## 実装
- `setup_bench_policy.py` = v009(exp018 discipline) + `choose()` override（SETUP_BENCH_POKEMON 時のみ）。
  優先度（Phantump100>Dunsparce80>Cramorant40>Snorlax30>他10）で並べ、**cap 枚まで**。
  ただし**最低1体は backup として残す**（active KO 即負け回避）。Crustle 壁相手は base 通り全展開。
  cap は env `SETUP_BENCH_CAP`（既定3）で sweep 可。built artifact で独立評価（contamination 回避）。

## 結果（built artifact, n=200 ペア, err 0）
- **ミラー vs v009**: cap2 **0.515** / cap3 0.480 / cap4 0.495。**全て 0.50±1SE 内＝有意差なし**。
  （ミラーは**引き分け率 51%**＝デッキアウト/タイムアウト飽和。prize 差で決まっていない。）
- **フィールド回帰チェック（cap3 vs v009, n=100）**: lucario_ex +0.01 / Crustle −0.01 / Alakazam −0.04 / dragapult +0.03。**ほぼフラット**。

## 診断（`diag_setupbench.py`, なぜ効かないか）
- 100 ゲームで setup-bench 判断は46回のみ。**base が並べる basic 平均 = 1.41 枚**。
- **>2 体提示 4.3% / >3 体提示 0%**（max=3）。**cap3 は一度も発火せず**（cap3≈v009 0.480 と整合）、cap2 も 4.3% でしか発火しない。
- 原因: 我々のデッキは**basic-light**（Phantump×4/Dunsparce×4/Snorlax×2＝10/60）。
  セットアップで手にある basic は1-2体で、しかも**それらは並べたい line そのもの**＝規律で削る余地がほぼ無い。

## 結論（誠実な負・無害な no-op）
- disc708586 の「全 basic 並べ」は**仕様としては真だが、basic-light な我々のデッキでは実害ゼロ**＝改善余地なし。
  「全 basic flood」の懸念は **basic-heavy デッキにこそ効く**話で、我々の archetype には当たらない。
- ミラーの 51% 引き分けは、ミラーが**飽和（deckout/timeout）**で決着している証拠＝
  セットアップ規律のような序盤の微調整では動かない（前回の「ミラー実行の上積みは頭打ち」と整合）。
- **不提出**（改善なし、cap2 でも 4% の試合しか触らず無計測ゲイン）。v009 据え置き。

## レポート価値
- 公式ドキュメントから「pilot のバグ的挙動」を発見→仮説→**測定＋診断で no-op と判明**＝
  「信じる前に測る」「deck⊗pilot（basic-light だから setup 規律が不要）」の好例。
- 一般教訓: **セットアップ規律は basic-heavy デッキの最適化レバー**。我々の S1 非ex は元から lean。

## 再利用資産
- `setup_bench_policy.py`（SETUP_BENCH 規律, env で cap 可）/ `eval_setupbench.py`（ペア比較）/ `diag_setupbench.py`（発火率計測）。
