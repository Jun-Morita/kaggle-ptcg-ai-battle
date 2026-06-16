# exp001_harness — SESSION NOTES

## 仮説
ローカルで任意の2エージェント (`agent(obs_dict)->list[int]`) を対戦させ、勝率・サイド差・
手数・1手の思考時間を集計できる再利用ハーネスを作る。以降の全エージェント開発の評価基盤にする。

## 構成
- `harness.py`: エンジン(`cg`)ロード, `run_match`, `run_gauntlet`, 結果データクラス。
- `agents.py`: `make_random_agent`（固定デッキ→合法ランダム選択）。
- `run_gauntlet.py`: エントリ。seed 適用, 結果を `results/baseline_random.json` に保存。
- `run.sh`: `uv run python run_gauntlet.py`。

## 設計上のポイント
- エンジンは単一バトルのグローバル状態（`Battle.battle_ptr`）。試合は逐次実行。
- デッキ収集フェーズ: `obs.select is None` の観測を渡してエージェントに60枚デッキを返させ、
  その後 `battle_start(deck0, deck1)`（Kaggle 本番ハーネスと同じ手順）。
- 各選択は `o.current.yourIndex` の手番エージェントを呼ぶ（部分観測=各自の視点）。
- `swap_sides=True` で先攻/後攻バイアスを相殺。結果は agent0 視点に正規化。
- 例外を投げたエージェントは反則負け（相手の勝ち）。

## 結果 (2026-06-17, random vs random, n=20, seed=42)
- winrate(agent0) = 0.600 (w0=12 / w1=8 / draw=0) — n=20 のノイズ範囲（±0.11 程度）。
- avg_moves = 36.6 / max_move_time ≈ 0.005s / wall = 0.20s (≈10ms/game)。
- 勝敗理由: **reason=3(バトル場ポケモン不在)=18, reason=1(サイド0=正規勝利)=2**。

## 考察 / 次への示唆
- ランダムはほぼ「セットアップ失敗＝自滅(reason3)」で決着。正規にサイドを取り切る勝ち(reason1)は稀。
  → **基本ポケモンを場に出し維持するだけの最小ルールベースでランダムを圧倒できる**見込み。
- ハーネスは高速（10ms/game）。数千〜万試合の評価が現実的。探索エージェント導入後は遅くなる前提。

## 次アクション
1. ルールベース agent v1: セットアップ正常化（基本ポケモンをアクティブ/ベンチに置く、END で投了しない、
   攻撃可能なら攻撃）。random に対する勝率を測る。
2. 観測→合法手の意味付けユーティリティ（OptionType ごとのハンドラ）を `agents.py` か別 util に。
3. 評価相手プール（random, rulebase, 旧self）を作り gauntlet 化。

## 出典
- エンジン/サンプル: Simulation コンペ `pokemon-tcg-ai-battle` の `sample_submission/`。
