# Knowledge Index

Claude Code はまずこの index を読み、必要なファイルだけ開く。

## Files

| File | Purpose | When to read |
|---|---|---|
| `notebooks.md` | Public notebook 由来の知識 | baseline、特徴量、モデル案を探すとき |
| `discussions.md` | Kaggle discussion 由来の知識 | ルール、リーク、CV/LB差分、重要な注意点を確認するとき |
| `external_ideas.md` | 論文、記事、他コンペ由来の知識 | 外部手法やモデル候補を検討するとき |

## Current Highlights

- PTCG AI Battle = Simulation(エージェント提出) + Strategy(賞金$240k・レポート)。Strategy 評価は安定性/デッキ/Simulation成績 → 強いエージェントが前提。
- エンジン `cg`(libcg.so, ctypes) はローカル動作確認済み。観測=部分観測、行動=option index list。
- **前方探索 API `search_begin/step/end`** あり（相手隠し情報を予測値で渡す determinization）。MCTS/ルックアヘッドの基盤。

## Experiment Candidates

- exp001: ローカル対戦ハーネス（2 agent 対戦, 勝率/サイド差/手数集計）。【完了】
- exp002: ルールベース5種(公式4+V2)+random 総当たり表。【完了】強さ: lucario_v2 0.680 > v1 0.647 > dragapult 0.573 > abomasnow 0.543 > iono 0.520。越えるべきバー=0.680。公開V2の勝率主張(91%)は再現せず(実測55%)。先攻有利ほぼ無し。
- exp003: Search API で1手読み（攻撃の実ダメージ/勝敗評価）軽量agent。
- exp004+: 公式 MCTS/RL サンプルを動かし determinization・相手モデルを改善（本命）。
- デッキ最適化（4公式デッキを改良 / 使用可能プール内で勝率最大化）。
- 運営公開ノートブック詳細は `notebooks.md`、raw は `references/raw/official_notebooks/`。

## Rule / Leakage Notes

- Rules 確認済 (`references/raw/kaggle_pages/*_rules.md`): external data 許可 / pretrained 許可（勝者 MIT 公開義務）/ 5提出/日。Pokémon要素学習モデルはコンペ外利用禁止。
- エンジン=cabt (kaggle-environments 1.14.10)。提出 .tar.gz。レーティング TrueSkill系 μ0=600・勝敗のみ・最新2提出。
- **Strategy ルーブリック**: Model70%(明快さ/独創性/安定性/頑健性/LB) Deck20% Report10%。Writeup≤2000語。LB上位は必須でない。
- 1試合10分・タイムアウト敗北 → 1手の探索予算に制約。
- ローカル自己対戦で「真の隠し情報」を探索に渡すと過大評価。本番はサンプリング必須。
- 要取得: Simulation discussion 708586（公式ルール vs シミュレータ差分）、cabt API docs。

