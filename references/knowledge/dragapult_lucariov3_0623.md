# 公開ノート2点（2026-06-23）: 強 Dragapult ex / Lucario v3 anti-Crustle

- raw: `references/raw/public_notebooks/{phantom-dive-or-go-home-a-dragapult-ex-deck, ptcg-915-lucario-v3-anti-crustle-search}.ipynb`（Git管理外, 各 main.py＋deck 付き）。公開＝利用可。

## 1. Phantom Dive: 強 Dragapult ex ★重要
- **よく操縦された Dragapult ex**（rule-based スコアリング, 32KB）。Phantom Dive spread＋**Budew アイテムロック**＋
  **Crushing Hammer エネ破壊**＋Boss's Orders＋デッキアウト回避。デッキ: Dreepy4/Drakloak4/Dragapult ex3/Budew2/
  Fezandipiti ex1/Latias ex1/Meowth ex1 ＋ Poffin/Ultra Ball/Crispin/Crushing Hammer/Lillie/Boss/Rare Candy/Watchtower。
- 著者主張(実ラダー head-to-head): **Mist 壁/Colress(~25%) 81% / Petrel-Trevenant(~10%) 79% / Mega Lucario(~15%) 50% /
  Alakazam(~12%) 有利**。「format 最高勝率 archetype だが ~6% しか使わない＝手で回すのが fiddly だから＝rule-based の隙」。
- **我々への含意（exp017 を覆す）**:
  - exp017 で「Dragapult vs ex 0.19」→不提出としたが、それは **baseline(exp002 dragapult.py)の弱い操縦**が原因。
    **良い操縦なら ~50% vs ex・~80% vs 単サイド** ＝ **deck⊗pilot 密結合**の再例（弱pilot→0.19 / 強pilot→競争力）。
  - **脅威**: この強 Dragapult は **我々の v009 非ex(Mist Energy 採用の単サイド)を ~80% で狩る**可能性大（spread が単サイド低HP を分散で取る）。
    Dragapult 採用が増えれば我々が counter される。要・実測（v009 vs 強Dragapult）。
  - **機会**: 強 Dragapult は支配的な単サイド field を食い ex と五分＝現メタの有力候補。ただし(a)他者実装＝Strategy 独創性は低、
    (b)メタは ex 復権中(39%)で Dragapult は ex に五分＝期待値は局面次第、(c)Stage2 setup の brick ~10%。
- 採用方針: **強 Dragapult を評価プールに追加**（baseline でなく real な脅威で v009 を測る, 3rd-party 実行は要承認）。
  そのまま提出はしない（独創性）。spread 耐性のヒント（Budew/Crushing Hammer の使いどころ）。

## 2. Lucario v3 anti-Crustle: 新規性低
- Mega Lucario ex ＋ **Crustle(345)回避→非ex Hariyama ルート** ＋ forward-search ＋クラッシュ安全 ＝ **我々の v003(exp007)と同型**。
  メタが Crustle を離れたため直接価値は低い。参考: 他公開エージェントのポインタ(Nithin compact Lucario, Roman V9/V10,
  Ryota Alakazam, tomatomato Starmie)、anti-stall END ガード、optional 選択に負スコアを入れない安全策。

## 出典
- Phantom Dive Dragapult ex（公開ノート, 著者の実ラダー head-to-head 主張）。
- Lucario v3（penguin069/romanrozen/kacchan/kojimar/pilkwang を参照と明記）。
- 関連: 我々の exp017(Dragapult メタ・タイミング, 弱pilot で不提出), [[meta-and-leaderboard]] deck⊗pilot。
