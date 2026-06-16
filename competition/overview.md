# Competition Overview

Pokémon Trading Card Game (PTCG) AI Battle Challenge。**2つの対になるコンペ**で構成される。

- **Simulation**: `pokemon-tcg-ai-battle` (Knowledge, 賞金なし) — AI エージェントを提出し、自動対戦でライブレーティング。
- **Strategy**: `pokemon-tcg-ai-battle-challenge-strategy` (賞金 $240,000) — Simulation に出したエージェントの戦略レポートを提出。

> 重要: Strategy の評価軸は「①エージェントの安定性 ②デッキ設計コンセプト ③Simulation での成績」。つまり **賞金を狙うには、まず Simulation で強いエージェント＋デッキを作ることが必須**。両コンペを一体で進める。

## Basic Info

- Competition: Pokémon TCG AI Battle Challenge (Simulation + Strategy)
- URL:
  - Simulation: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle
  - Strategy: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy
- Official site: https://ptcg-abc.pokemon.co.jp/
- Organizer: Kaggle / co-organizers: The Pokémon Company, Matsuo Institute, HEROZ / support: Google Cloud, NVIDIA
- Deadline:
  - Simulation 提出: 2026-06-16 20:00 JST 〜 2026-08-17 08:59 JST (Kaggle 表記 2026-08-16 23:59 UTC)
  - Strategy 提出: 2026-06-16 20:00 JST 〜 2026-09-14 08:59 JST (Kaggle 表記 2026-09-13 23:59 UTC)
- Task type: 対戦ゲームの行動方策エージェント（逐次的意思決定）＋デッキ構築。部分観測・確率的（コイン/シャッフル）。
- Target: 60枚デッキを構築し、各選択局面で最良の選択肢 index を返すエージェント。
- Metric: Kaggle 独自レーティング（継続対戦のスキルレーティング, ライブ LB）。Strategy は上記3軸の審査。
- Submission limit: Simulation 5/日, Strategy 1チーム1回。
- 賞金 (Strategy): 1次1〜8位 各$30,000 + 2次進出 / 2次 優勝$50,000・準優勝$30,000 / 2次参加者 各$3,000 GCPクレジット。

## Data

- Download source: Kaggle competition files（両コンペで同一のカードデータ）。
- Local path: `data/raw/{EN,JP}_Card_Data.csv`。エンジン同梱物は `data/sim_sample/`。
- カードデータ: `EN_Card_Data.csv` 2102行(ヘッダ除く)。列: Card ID, Card Name, Expansion, Collection No., Stage/Type, Rule, Category, Previous stage, HP, Type, Weakness, Resistance, Retreat, Move Name, Cost, Damage, Effect Explanation。
- エンジン経由カードデータ: `all_card_data()` で 1267 件の `CardData`、`all_attack()` で技データ。
- Card ID List PDF (EN/JP, 大きい): 使用可能カードプール一覧。Standard ベースだが本大会用に限定。
- Key columns / IDs: `Card ID`（デッキ・観測・探索 API すべてで使う一意キー）。
- 60枚デッキ。ACE SPEC は1枚まで。基本エネルギーは枚数制限なし(サンプルデッキで card id 3 を多数採用)。

## Metric

- Official definition: Simulation は **TrueSkill 系レーティング** N(μ,σ²)。初期 μ0=600。勝敗のみ反映（点差は無関係）。勝ちで μ↑/負けで μ↓/引分は平均へ。σ は情報量で減少。**最新2提出のみ最終評価に使用**。提出時に self 対戦の Validation Episode を実施。締切後 約2週間継続対戦して LB 確定。Strategy は上記ルーブリック審査。
- Local implementation plan: ローカルで自己対戦/対ベースライン勝率を主指標にする（勝率, 平均サイド差, 平均手数）。Kaggle レーティングそのものはローカル再現不可。
- Direction: higher is better（勝率/レーティング）。
- Sanity check: `data/sim_sample/cg` でランダム agent 同士の自己対戦が完走することを確認済み（下記 Validation 参照）。

## Validation

- Fold method: 通常の CV ではなく **対戦ベース評価**。固定の対戦相手プール（ランダム, ルールベース, 旧バージョン self）に対する勝率で評価する gauntlet 方式。
- Number of folds: N/A（代わりに対戦数 N を十分に取り 95% CI を見る）。
- Grouping key: N/A。
- Stratification key: 先攻/後攻, 対戦相手の種類でバランスを取る。
- Leakage risks: 探索 API で相手の隠し情報（手札/山札/サイド）を「予測値」として与える設計。本番では未知なのでサンプリングが必要。ローカル自己対戦で真の隠し情報を使って過大評価しないよう注意。
- Fold file: N/A（評価対戦の seed セットを `workspace/` に保存予定）。
- CV/LB correlation check: ローカル勝率 vs Kaggle LB レーティングの相関を提出ごとに記録する。

## Submission

- Type: **cabt Engine**（kaggle-environments 1.14.10 用の PTCG シミュレータ）の episode 型。エージェントは `/kaggle_simulations/agent/` 配下に展開。API docs: https://matsuoinstitute.github.io/cabt/
- 提出形式: **`.tar.gz`**（`main.py` をトップレベル=ネストしない, `deck.csv` 同梱）。`tar -czvf submission.tar.gz *` で作成し My Submissions からアップロード。
- Required file: `main.py`（`agent(obs_dict) -> list[int]` を実装）, `deck.csv`（60行のCard ID）, `cg/` パッケージ同梱。
- Required columns: deck.csv は1行1 Card ID（60行）。
- Agent 仕様:
  - 初手: `obs.select is None` のとき 60枚デッキ(list[int]) を返す。
  - 以降: 各選択で option index の list を返す。長さは `minCount <= len <= maxCount`、重複不可、各要素 `0 <= i < len(option)`。
- ID order / Value range: 選択肢 index は提示順。Card ID は CardData の ID。
- Local validation: `game.battle_start/battle_select/battle_finish` でローカル対戦可。本番同様 `agent()` を呼ぶハーネスを自作する。

## Rules（Kaggle Rules タブ取得済み, `references/raw/kaggle_pages/*_rules.md`）

- External data: **許可**。公開かつ全参加者が低コストでアクセス可能（Reasonableness Standard）であること。コンペデータはコンペ目的のみ・終了後削除。
- Pretrained models: **許可**（external models acceptable unless prohibited）。ただし勝者は提出物とソースを **MIT 等 OSI ライセンスで公開義務**。非互換ライセンスのデータ/事前学習モデルを使うとその部分は公開不要だが勝者要件に影響。
- Pokémon Elements で学習したモデルはコンペ外利用・商用利用・競合製品作成が禁止（参加者がモデル重み等の権利は保持）。
- Internet: Rules の "INTERNET" 条項(15)は免責文言で**エージェント実行時のネット可否ではない**。実行時のネット可否は cabt/kaggle-environments 環境依存（エピソードはサンドボックス実行=オフライン想定）。要 cabt docs 確認。
- 制限時間: 1試合最大10分、タイムアウトは敗北。1手あたりの予算は kaggle-environments の actTimeout 依存（要確認）。
- AMLT（AutoML）使用可。private 共有はチーム内のみ。public 共有は Kaggle forum 上で OSI ライセンス。
- 1アカウント1人。提出 5/日。Winner license type: MIT。
- 公式 PTCG ルールとシミュレータの差分: Simulation discussion 708586 を参照（未取得・要確認）。
- Last checked: 2026-06-17（Kaggle Rules タブ md 取得済み）。

## Strategy 評価ルーブリック（Hackathon, $240k = 8 Finalists × $30k）

- **Model Score 70%**: ①アプローチの明快な articulation ②独創性・技術的妥当性 ③反復対戦での安定性 ④初期状態/マッチアップ/運への非依存(頑健性) ⑤Simulation track 成績。
- **Deck Score 20%**: デッキコンセプトの明快さ＋戦略との整合、キーカード選定・活用。
- **Report Score 10%**: 構成の論理性・明快さ、図表の有効性。
- 提出: Kaggle Writeup（**2000語以内**）＋ Media Gallery（図/動画）。Track 選択必須。締切 2026-09-13、審査 09-14〜10-11。
- 重要: **LB 上位は有利だが必須ではない**。中下位でも深い分析・独創性・優れたレポートで高得点可。→ 「安定・筋の通った agent + デッキ + 明快なレポート」を狙う。

## エンジン API 要点（`cg` パッケージ）

- `cg.game`: `battle_start(deck0, deck1)`, `battle_select(list[int])`, `battle_finish()`, `visualize_data()`。
- `cg.api`: 観測データクラス群（`Observation/State/PlayerState/Pokemon/SelectData/Option/Log` など）と enum（`OptionType`, `SelectContext`, `AreaType`, `EnergyType` ...）。`to_observation_class(dict)`。
- **探索 API（先読み）**: `search_begin(obs, your_deck, your_prize, opp_deck, opp_prize, opp_hand, opp_active, manual_coin)` → `search_step(search_id, select)` → `search_end()` / `search_release(id)`。
  - 相手の隠し情報は「予測 Card ID」として渡す必要がある（枚数は実値に一致必須）。→ MCTS/determinization の核。
- 隠し情報: 観測では相手の `hand` は None、`deck` は枚数のみ、伏せカードは None。
- 勝敗理由 (`LogType.RESULT.reason`): 1=サイド0, 2=山札0でターン開始, 3=バトル場ポケモン不在, 4=カード効果。
