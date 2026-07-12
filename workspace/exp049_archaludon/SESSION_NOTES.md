# exp049 — Archaludonデッキ複製: 「全員が負けるデッキに乗る」 → v020出荷

## 仮説
silver圏(933.4)への最短路はデッキ⊗メタの噛み合わせ。mixed_ex4/Archaludonは
メタシェア16%の現メタ頂点で、LB#1 taksai(0.28)・tomatomato(0.25)・我々の
v016壁(0.22)が**全員負ける**。倒す研究より使う側に回る方が速い。

## スカウト→デッキ特定
- tomatomatoキャッシュ(537試合)からmixed_ex4側の勝者を集計:
  Takaaki Matsuda 5-1, ezreal77 5-0, ShumpeiNomura 3-1(LB 1083.6, 最上位)等。
- `/extract-deck` ShumpeiNomura sub 54588173 → `exp011/archaludon_nomura_deck.json`
  (65/65試合同一60枚: Duraludon4/Archaludon ex4/Relicanth2/TR Articuno1 + 鋼12 +
  厚いサーチドロー)。

## パイロット検証（deck⊗pilotの再確認）
| 構成 | crustle | ex_lucario | 判定 |
|---|---:|---:|---|
| Nomura構成 + 汎用lucario_v2 | 0.000 | 0.067 | 完敗。汎用はArchaludonを操縦できない |
| **公開専用pilot + 自前Cinderace型** | **0.867** | **0.717** | 採用 |
| 公開専用pilot + Nomura構成 | 0.567 | 0.467 | 劣化。pilotのルールが自前デッキに調律 |

公開専用pilot = exp025で対戦相手として導入済みの公開notebook
「a-sample-archaludon-75-wr-vs-my-1300-starmie」(レビュー済み純ルールベース、
numpy不使用、`__file__`ガード済み)。

## 決定ゲート: n=200×6ガントレット（専用pilot+自前デッキ）
crustle 0.805 / ex_lucario 0.645 / dragapult 0.655 / starmie(tomatomato構成+
汎用pilot) 0.825 / **v016壁 0.825** / **v019チェーン 0.870**
= **合計4.625/6、全マッチ0.645以上、0エラー。ローカル計測史上最強。**

## ビルド・出荷
`scripts/build_submission.py`で自前クラッシュ安全ラッパー追加
(`--patch patch_mydeck.txt`で`my_deck = read_deck_csv()`を注入)。
スモーク0エラー、ビルド済み成果物 n=200 vs ex_lucario 0.660(直接評価0.645と
一致、スモークn=30の0.500はノイズ)、bare-execサンドボックスレプリカ148 acts
0エラー max_act 0.00s。

**v020-archaludonとして2026-07-12 08:43提出（ユーザー承認済み）。**
eligible = {v019-searchpri3, v020-archaludon}。v016壁は意図的にドロップ
（v020が壁の標的(grimmsnarl/starmie/crustle系)をより高い勝率でカバー）。

## リスク・留意
- 公開コード由来→同型ミラー増加の可能性（提出文に帰属明記済み）。
- ミラー(mixed_ex4 16%)での挙動は未測定。ラダー収束を/meta-watchで監視。
- starmie 0.825はtomatomato構成+汎用pilotが相手。実ラダーの熟練Starmie
  (taksai/tomatomato本人)はもっと強い可能性（exp048の教訓）。
