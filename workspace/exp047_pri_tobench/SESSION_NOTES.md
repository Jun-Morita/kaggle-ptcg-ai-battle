# exp047 — SEARCH_PRI pattern横展開: 学習済み状態条件付きDISCARDチューザー

## 背景
exp043v2(SEARCH_PRI2, TO_HAND)がshipped(v018)。ユーザー方針:
「SEARCH_PRI2の手法を他のselect文脈へ横展開しよう」。同じ構造的ギャップ
（`_score_card_choice`がそのcontextを一切スコアしておらず`return 0`で
tie→原順序の決め打ち）を持つ他のSelectContextを探索する。

## 文脈スカウト（Yushin Ito top_yushin_0708キャッシュ、n=1000リプレイ）
`extract_selects_ctx.py`（exp043のextract_selects2.pyを任意contextに一般化した版）で
出現頻度と複数選択肢率を確認:

| context | 出現数 | multi-option | 判定 |
|---|---:|---:|---|
| TO_BENCH | 550 | 434 | 検討 |
| DISCARD | 184* | 184 | 検討 |
| SETUP_BENCH_POKEMON | 83 | 20 | 少なすぎ |

*200リプレイでの粗い頻度。全1000リプレイで再カウントすると943件/786試合。

### TO_BENCH（デッキ→ベンチ, 山札サーチ効果）→ NO-GO
2207決定/972試合抽出。候補カードがPhantump/Snorlax/Cramorantの3種のみで
ほぼ決め打ち(常にPhantump優先)。**静的最頻値ベースライン0.910**に対し
学習モデルは0.775-0.854で全く届かず、エポック間も不安定。
**結論: 学習可能な状態依存がほぼ無い（3択・ほぼ決定論的）。見送り。**

### DISCARD（手札上限/効果による捨札選択）→ 有望、field/paired待ち
943決定/786試合抽出(`extract_selects_ctx.py DISCARD`)。候補19種、
pick数はほぼ3(773/943)。**静的最頻値ベースライン0.220**に対し学習モデルは
val top-1 0.34-0.42（game-level holdout n=50, 30エポック中最終0.360）
——TO_HANDほどの規模(n=8460/979試合、6.5σ)ではないが、明確に静的を
上回る方向性。val=50は小さくノイズも大きいため、field/pairedゲートで
決着させる。

## モデル・統合
`train_pri.py`（exp043から無改造で再利用、context非依存の設計）で
`results/discard1/pri.npz`を学習。`revenge_policy.py`に`SEARCH_PRI3`
env gateで統合（SEARCH_PRI2と全く同じ構造: `_gen_searchpri3()`が
npzをビルド時にリテラル辞書としてPATCH_SRCへインライン化、未知カードは
元の`choose()`へ保守的フォールバック）。

## ビルド・スモーク
`build_sp3/`（v014と同一レシピ: lucario_v2 + tb_patch + v_trev,
REVENGE_BONUS=50 SEARCH_PRI3=1）。`build_v014/main.py`とのdiffは
SEARCH_PRI3ブロックのみ（+既存の無効化済みTB_VALUEブロック、無関係）。
スモークn=30×3(lucario_v2/Crustle/dragapult) エラー0。

## ゲート
1. **決定ゲート = paired vs v014（別ビルド、eval_paired.py流用）**: n=200実行中。
   SEARCH_PRI2の教訓通り、field eval単独では判断せずpairedを最優先する。
2. n=200で有望なら n=600→n=1000まで積んで z≥2 を確認してから出荷判断
   （pre3b/SEARCH_PRI2で確立した規律）。

## 決定的ゲート結果: paired vs v014 (build_sp3 vs build_v014, 別ビルド, swap_sides=True)

| n | 内訳(W-L-D) | winrate | 累積z |
|---:|---|---:|---:|
| 200 | 102-94-4 | 0.510 | 0.28 |
| +400 | 225-172-3 | (累積600: 327-266-7, 0.545) | 2.20 |
| +400 | 211-186-3 | **累積1000: 538-452-10, 0.538** | **2.40** |

エラー0、全チャンク完走。**SEARCH_PRI2の最終z(0.76, n=1000)より明確に強い有意な
勝ち越し。** 横展開の最初の試行(DISCARD文脈)で当たりを引いた。

**判定: GO。出荷候補とする（ユーザー承認後 `kaggle competitions submit`）。**

## 経過
- 2026-07-12: 実装・ビルド・スモーク完了。paired n=200→600→1000で決定的GO。
  次: build-submitフロー(`/build-submit`相当)でユーザーに提出承認を仰ぐ。
  eligible枠は現在{v016-wall, v018-searchpri2}——本命提出するとどちらかが
  eligibleから外れる点に注意（v016-wall再提出のような対応要否をユーザーと確認）。
