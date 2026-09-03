# Kaggle discussion/kernel check — 2026-09-03

取得日: 2026-09-03。対象: pokemon-tcg-ai-battle の discussion（279件、0 new/20
updated — フォーラムは 08-31 の disc738307 以降静止）と kernel（60件、5 new）。
未読だった4スレッドと1 kernel を読了。

## 1. 【最重要・自分たちの Writeup に直結】Pokemon Elements 利用の公式回答

出典: disc736603（Charlie Lockyer, 08-21）。08-24 に Kaggle staff **Addison
Howard** が回答済み（我々は今回初めて確認）。

> Use of Pokémon Elements in your writeup as you've described is permitted and
> encouraged. Discussing board positions, card interactions, gameplay elements,
> character names, etc are all appropriate. You may also use screenshots from
> the official visualizer in your Writeups.
>
> It would not be appropriate to modify those Elements, create new elements
> based on those (e.g. don't make up your own Pokémon characters), or to
> suggest that your use of them in your Writeup is claiming ownership to them.
>
> Participants own the IP to their Submission, but do not claim ownership over
> the Elements cited in their Submission, and can't use the Elements in any
> prohibited way outside of the competition.

**確認できたこと**: カード名・技名・効果名・アーキタイプ名を本文で使うのは
明示的に許可（我々の writeup.md はこの形＝問題なし）。公式ビジュアライザの
スクリーンショットも可。

**確認できていないこと（グレーゾーン）**: 質問者が示した2択のうち「PTCG公式
ビジュアライザ（カードアートそのものを表示）」は本人が NG 予想で投稿したが、
回答は「official visualizer」としか言っておらず、どちらを指すか明言していない。
**カード原画そのものの複製・改変を伴う画像**（我々の `thumbnail.png` のように、
実在カードを描き起こした/生成したイラストを含む画像）が「modify」「create new
elements based on those」に該当するかは、この回答だけでは判定できない。
`thumbnail.png` は自作の人物アバター＋カード風のグラフィックを含む合成画像。
人物は完全オリジナルで問題ないが、**カードアート部分が実在カードの改変や
生成物である場合は解釈が分かれ得る**。断定はできない — 判断が必要なら現物を
Kaggle 側に見せて確認するのが安全。

## 2. 独立データで Grimmsnarl の弱点を再現 — Ogerpon ex 87.0% (n=69)

出典: disc737107（Marco Di Cio, 08-23、締切後 08-18〜08-22 の23,313試合を
アーカイブ日次データセットから解析、レーティング差50点以内に限定した厳密な
方法論）。

> Teal Mask Ogerpon ex vs Marnie's Grimmsnarl ex: 87.0% win rate, n=69,
> 95% CI [77.0%, 93.0%]

我々の writeup §2 で引用した kiyomiya-k の 95%(n=222) と**独立のデータソース・
独立の期間で同じ弱点が再現**されている。主張の裏付けとして強い。

## 3. Grimmsnarl は「補正すれば互角、しかし今は最上位でほぼ消えている」

同じ disc737107 のデッキ別テーブルから:

| 指標 | 値 |
|---|---|
| 全体シェア（entries） | 5.8%（6位、Dragapult ex 26.6%が最大） |
| 平均パイロットレート | 949（**全13デッキ中最低**） |
| 生の勝率 | 41.5% |
| ±50点以内に絞った勝率 | **48.0%**（+6.5pt） |
| 上位10%帯でのシェア | **<0.1%**（ほぼ消滅） |
| 下位60%帯でのシェア | **22.6%**（最頻出） |

パイロット強度を制御すると Grimmsnarl はほぼ互角（48.0%）まで戻る。これは
07-31 の discussion_intel_0731.md（Sumi, 補正後50.9%）と方向が一致し、
**「デッキ選択は不合理ではなかった、差はパイロット」という我々の報告の主張と
整合する独立の再確認**。

一方で新しい事実として: **締切後の上位10%では Grimmsnarl は事実上絶滅
（<0.1%）、下位60%では最頻出（22.6%）**。デッキが初心者の逃避先になっている
という構図。

**我々の writeup.md への含意（要検討・編集は09-13まで可能）**:
本文 §2 冒頭 "the most-played archetype on the ladder" は、我々がデッキを
選んだ時期（07-26頃、上位帯シェア51.3%、`pokemon_names_ja.md` 記録）には
真だったが、**締切後のデータでは Grimmsnarl は6位・上位帯でほぼ消滅**しており、
時点を明示しないと不正確に読める。日付を添えるか、文言を弱める価値がある。
ただし本文の主張（バイアス・ドリフト・分散の三分解）自体への影響はない。

## 4. TrueSkill パラメータの独立推定 + 「シルバー確率」への懐疑

出典: disc737435（KaizaburoChubachi, 08-25, 25票・12コメント）。Meta Kaggle
の全エピソードから Bradley-Terry + 実測head-to-head のハイブリッドでモンテ
カルロシミュレーション（500回、14日×96試合/日、TrueSkill風更新、μ0=600）。

推定パラメータ: 初期σ=200, β=100, τ=2（公式は未公表、著者の推定）。

**コメント欄の指摘が我々の報告の主張と直接共鳴する**:
> 李秉叡（ntumlnoob）: "My gold chance should be quite a bit lower... the SD is
> underestimated here."
> 著者本人も同意: "if uncertainty in the win-rate estimates were incorporated,
> I'd expect the variance to increase."

**我々が §4.1 で使った kiyomiya-k の sd=51（7回の同一提出）を補強する、
別ソースからの「公式の分散推定は過小」という指摘。** 数値を writeup に足す
必要はないが、報告の中心テーゼ（ラダーの分散は見た目より大きい）が
コミュニティの認識とも一致していることの確認。

## 5. kernel: pokesom「Rule-Based Dragapult ex — Solution Write-up」(08-17)

ルールベースのみで Dragapult ex を操縦する詳細な設計。3本柱:

1. **固定スコア帯のラダー**（Lethal 660-830 > 進化 700+ > 効果/サポート
   300-660 > サーチ 350-660 > エネ手貼り 292-299 > 攻撃 240-265 > ターン終了
   10）— 優先順位が監査可能・テスト可能な形。
2. **リーサル全探索**: ばら撒き(Phantom Dive)のベンチ対象部分集合を2⁵=31通り
   総当たりで厳密に解く。**「まだ使っていない資源」込みのリーサルも予約**
   （手貼りで完成する力/アドレナブレイン起動/Boss's Ordersでの呼び出し）。
   Boss's Orders は「使わないと勝ち切れない」場合のみロックして最優先。
3. **ミラー特有の防御ルール**: 自分のドロンチ(Drakloak)が露出している時、
   相手をダメカン3個以上のせて放置しない（アドレナブレインの的になるため）
   — 2個までに制限。

我々の agent は imitation-only で、この種の「厳密なリーサル解決 + 資源予約」
は持っていない。§6 で引用した rick/Ozturk の知見（スループット・ポートフォリオ
fine-tune）とは別の軸 — **ルールベースでも致死判定を全探索すれば、模倣より
強い決定的な一手を打てる**という具体例。次シーズンがあれば検討候補。

## 6. その他、目を通したが低優先度

- disc738058: Strategy-only エントリの賞金資格質問。host 回答
  "mathematically possible, highly unlikely" — 我々には無関係（Simulation
  済）。
- disc738307 "Crazy LB shake & shake"（08-31, 1コメント）: 個別チームの順位
  変動の愚痴、学びなし。

## まとめ

今回で最も重要なのは **#1（Pokemon Elements 公式回答）**。カード名の使用は
公式に許可されており本文は問題ないが、`thumbnail.png` のカードアート部分は
グレーゾーンの可能性がある — 断定はできないため、気になる場合は現物を確認
してもらうのが安全。**#2/#3（独立データでの Ogerpon 弱点再現・パイロット
補正後は互角）は我々の writeup の主張を裏付ける良い外部証拠**（本文への追加
は必須ではない）。#4 は分散過小評価という報告の中心テーゼの独立な傍証。
