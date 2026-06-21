# exp015_tactical — 終盤の戦術的探索レイヤー（設計）

## 0. 一文
exp014 は「**学習 value は中盤で破綻するが終盤(near-terminal)は AUC 0.80 で読める**」を示した。
ならば **エンジンの正確な前方探索を near-terminal 限定で使う**＝「このターンに KO/リーサルが取れる
選択肢」を正確に判定し、v008 のヒューリスティックが取りこぼす KO を拾う。学習しない。全証拠と整合。

## 1. 鍵となる観察（なぜ効くか・なぜ exp008 の罠を回避するか）
- **自ターン内は完全情報に近い**: 相手は動かず、自分の手札も見える（リプレイでも 2985/3002 で hand 可視）。
  → exp008 が苦しんだ「placeholder の相手に planning」は**自ターン探索には無関係**（相手が行動しない）。
- KO/プライズ取得は**離散で確定的な near-terminal イベント**＝評価が信頼できる領域（exp014: 終盤 AUC 0.80）。
- v008 `_plan_attack` は **ハードコードのダメージ推定**で KO 判定 → 弱点/道具(Choice Band)/boost(Postwick,
  Extra Helpings)/手順が絡む KO を取りこぼし得る。エンジンの正確な解決ならそれを拾える。

## 2. v1: 1手先プライズ最大化オーバーライド（最小・安全・即測定）
- 各 select（自手番・maxCount==1・選択肢≥2）で、各選択肢 i を `search_begin → search_step([i])` で1手だけ進め、
  **その手で取れたプライズ数**（= 自分の残プライズ枚数の減少）と**勝利(result==my_index)**を正確に測定。
- `base`（v008）の選択肢が取るプライズより**厳密に多く取れる or 勝てる**選択肢があれば乗り換え、なければ base。
  → 保守的オーバーライド＝**v008 を下回らない**（exp008 の margin と同じ安全性）。
- 1手先でも、攻撃→対象が別 select でも、プライズが確定する select で gain が出る＝**正しい KO 対象/攻撃を選ぶ**。
- 決定化: your_deck は**自分の実デッキリスト**から sample（ドローしても妥当）、相手隠れ情報は placeholder
  （相手は自ターン動かないので無害）。クラッシュ安全（例外→base, search_end 必ず）。手番時間キャップ。

## 3. 評価（go/no-go）
- 主指標: **tactical(charmq) vs v008(charmq) ミラー > 0.50**（同一デッキ＝純粋に探索レイヤーの寄与）。
- 退行なし: vs lucario_v2(ex) / Crustle が v008 を下回らない。速度 < 数百ms/手。
- 合格なら v009t としてビルド候補（`/build-submit`）。不合格でも誠実に記録（レポート素材）。

## 4. 拡張余地（v1 が効けば）
- v1b: 浅い複数手探索（道具/Boss → 攻撃の手順で初めて成立する KO）。budget 制限の DFS。
- v1c: 相手の次ターン lethal 回避（相手 active を残すと返しで負ける局面の検知）＝near-terminal の守備側。

## 5. 成果物
- `tactical_search.py`: `make_tactical_agent(deck)`（v008 を base に 1手先オーバーライドを被せる）。
- `eval_tactical.py`: ミラー＋対 ex/Crustle で v008 と比較。
- 出典: exp014（終盤可・中盤不可）, exp008（search API/決定化, agent_pimc.py）, exp013（v008 router）。
