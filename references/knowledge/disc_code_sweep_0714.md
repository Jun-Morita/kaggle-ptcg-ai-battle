# discussion/code 新着スイープ 2026-07-14（07-13スイープとの差分）

## 最重要3件

### 1. 【公式回答】マッチングの10%はランダム相手（disc724904, staff Addison Howard, 07-13）
> "Your submission has a 10% chance of facing a random opponent at any given matchmaking draw."
- 含意: (a) 帯域プールは厳密には「90%帯域＋10%全体場」の混合が正 (b) レートノイズの機構的
  一因 (c) 低レート帯の相手と当たっても異常ではない。

### 2. TR Spidops（非exアグロ）は「トップ10級」だった — 4%フリンジではない
v023に3-0したMarshall Maximizerを現LBで照合: **9位・1146.2**。paistiecoも143位(961.8, silver圏)。
- TR Spidopsは壁(#7 Budewに3-0)とLO(我々に3-0)の両方＝**Safeguardメタ全体のキラー**として
  gold帯下端に既に定着。次のメタ回転の起点候補として監視優先度を最上位に引き上げ。
- 公開ソースは上位40 kernel×2ソート・100 discussionのキャッシュに見当たらず（私的ビルドか圏外）。
- 対TRの勝ち筋は未実測（Majkel Alakazamは1-0のみ、壁は0-3、我々0-3）。

### 3. 30,000試合のタイミング解析でトップ勢の実装を推定（disc724362, 44票, Abhyuday）
- 手法: 起動時間＋手番思考時間の分布から実装を推定。**場の大半はルールベース**（半分は公開bot）。
- **トップ勢もほぼ探索なし**。#1のみ「重いモデルロード＋時間フル活用＝RL+bounded search」らしき挙動。
- 投稿者自身の証言: 「価値関数が正確でないと探索は効かない。不完全情報で探索は難しい」
  ＝我々のexp015/033/045の負の結果と独立に一致（レポート素材）。
- コメント: RL勢は1.7M paramで8秒ロード、5M paramで40秒ロード等の実例。

## その他
- disc711741（マルチデッキ可否への host 回答）: **依然0回答**（24票）。エージェントは毎試合
  デッキを差し替え可能な構造だが、可否不明＝コンプライアンスリスクとして手を出さない。
- disc724831（Rule 3.5.d: 非参加者の人間によるリプレイレビュー協力の可否）: 未回答。静観。
- kernel「1084.5 Baseline」(makthanithin): Mega Lucario ex系ルールベース＋対Crustleガード。
  コピーが増えれば**我々に好都合**（v023はlucarioに実戦7-0）。
- kernel「STRONG START V10 LB950+」(romanrozen, 122票): **Archaludon＋Alakazam/Dunsparceの
  ペア配布**——現帯域のArchaludon/Alakazam大量発生の供給源の可能性大。どちらもv023の得意客。
- naoto714のSlowking(コピー攻撃)/Mega Gengar探索ノート: 新アーキタイプの芽、現状シェアなし。
