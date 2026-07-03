# 公式エンジンソース公開（disc 717141, 2026-07-01）— 精査メモ

- 取得: `references/raw/ptcg_engine/`（30ファイル, C++20 header-only, gitignored）
- **ライセンス**: コンペ参加目的のみ・再配布/公開禁止・コンペ終了後に削除・派生物も "Pokémon Elements"。
  README/LICENSE の削除改変禁止 → raw ディレクトリにそのまま保持。**バグ悪用は規約で禁止**。
- 主要ファイル: `CardImpl.h`(13.7k行, 全カード定義), `SatisfyCondition.h`(全条件判定),
  `Search.h`(forward-search 実装), `GameProc.h`(ターン進行), `SelectProc.h`(option 生成),
  `EffectProc.h`/`EffectInstant.h`/`EffectContinual.h`(効果), `BattleData.h`(State/履歴)。

## 確定した事実（我々の実装に直結）

### 1. Horrifying Revenge の正確な発動条件（v011-v013 の window は近似だった）
`CardImpl.h:10754` + `SatisfyCondition.h:130`:
- 条件 = `state.turnHistories[1].koAttackDamageHop` ＝ **「前の相手の番に、ワザのダメージで、
  自分の Hop's ポケモンが気絶した」**。
- 我々の v011 window proxy「相手が前ターン以降サイドを取った」は**偽陽性あり**:
  (a) **非Hop's（Dunsparce 305 / Dudunsparce 66）が KO された場合**、(b) ワザダメージ以外での気絶。
- RB=50（+100 でなく中庸値）が最良だったのは、まさにこの偽陽性への頑健化だったと**機構的に説明がつく**。
- **改善候補（v014）**: obs から「前相手ターンに Hop's が場から消えた」を正確に検出（盤面/トラッシュの
  Hop's id 差分）→ window が正確になれば RB を 100 に上げても安全になるはず。要 n=200 検証。

### 2. Search API の determinization（Stage 2 の設計根拠）
`Search.h`: `search_begin` は渡された hidden 情報（myDeck/myPrize/enemyDeck/enemyHand/enemyActive）を
**そのままの並びで State に配置**（自前 shuffle 必須＝既に実施済み）。`shuffle(id, playerIndex)` API も
存在（山札だけ再シャッフル可能）。search は State の完全コピー上で走る＝**供給した仮説の下で完全決定的**。
belief の質がそのまま探索の質になる、という exp008 の結論をソースが裏付け。

### 3. その他
- turnHistories[] に ko / koAttackDamage / koTeamRocket / koAttackDamageEthan / koAttackDamageHop 等の
  フラグ群 → 「リベンジ系」条件は全てこの正確な履歴で判定される（同型カードのモデル化に流用可）。
- `SameAttackPreMyTurn`（前自ターンと同ワザ）等、我々が知らない条件タイプが多数 → 相手デッキの
  カード挙動を正確に読む辞書として CardImpl.h が使える（例: 対戦相手の攻撃の実効果確認）。

## 使い所
- pilot のダメージ/効果モデルの答え合わせ（推測ヒューリスティック → 仕様準拠）。
- Stage 2 belief-PIMC の相手モデル精度向上。
- Strategy レポート: 「観測から機構を推定 → ソース公開で検証された」という再現性の物語に使える
  （RB=50 の頑健性の機構的説明はレポート向きの材料）。

## ネイティブビルド（2026-07-03 検証済み）
- 全42ファイル取得（`references/raw/ptcg_engine/`）。ビルド:
  `g++ -std=c++20 -O2 -fPIC -shared Export.cpp -o libcg_local.so`（g++ 11.4, 15秒, 警告なし, 1.4MB）。
- **公式 cg パッケージと完全互換**: `cg/libcg.so` を差し替えるだけで battle_start/select/finish 動作。
  乱択自己対戦 20/20 完走、~10,300 steps/s（Python 往復込み）。
- 用途: (1) ローカル評価スループット向上（-O3/march=native 可）、(2) **大規模自己対戦データ生成**
  （exp014 の「価値較正はデータ不足が交絡」を 100-1000 倍データで再テスト可能）、(3) 計測器の埋め込み。
- 注意: 提出物には使わない（本番は公式エンジン固定）。ライセンス上ビルド成果物も外部共有不可。
