# Discussion / Code intel 2026-07-25

- 取得日: 2026-07-25
- 対象: pokemon-tcg-ai-battle（Simulation）
- 方法: nvidia-kaggle-skill（discussion_ingest 60スレッド/249コメント、kernels list 40件、LB突合）
- 文脈: v038 dragapult 転換直後。収束/分散・エンジン更新・公開エージェント上限を確認。

## 1. 収束・分散の機構（reroll 戦略の根拠, disc728695/728243/728935）

- **disc728695（Mando コメント）**: 「最初の数時間はスコアが乱高下（±80-100/試合）、その後は変化が
  極端に遅くなる（数十〜1桁）。**高レートのエージェントは基本、序盤で好成績だったもの。後で負けても
  減点が小さいから**」。＝TrueSkill σ が早く縮む＝**序盤ロックイン**＝reroll（良い早期ドロー）は効く。
- **disc728935（Addison 公式回答）**: 「**Bo1 は維持**（Bo3 にしない）」「**締切後に episode 頻度を上げる**」。
  → 後半は試合数増だが σ は既に小さく μ の動きは遅い＝序盤ロックイン＋真の実力の遅い圧力の両方。
- **結論（我々の運用）**: 真の archetype 強度（dragapult 0.576 > koff 0.492）は序盤も後半も有利＝
  最終LBに効く。**dragapult×2（強archetype×2ドロー）は両面で正当**。序盤数時間を監視し、
  片方が高く出たらロックイン期待、両方低ければ早期リロール（koff式運用）。
- disc728243（Tony Li）実務指針: 実績提出は守る/数百試合seat均衡+独立2回/大改善以外で強エージェントを
  再起動しない/同一2重提出は「luckyな方を選ぶ」のは可（LB=max）。＝我々の規律と一致。
- 参考: 「Bo3 は Bo1 より substantially 安定（20,000試合シム）」「提出間で受信episode数が 6-10倍ばらつく」。

## 2. エンジン更新（disc728587/728068）

- **disc728068**: Ninetales(#660)×Amarys(#1207) の相互作用で SIGSEGV（07-17ビルド）。Ninetales の
  「top 捨て→Supporter なら発動」が Amarys(DelayEffect) を借りると delay skill を攻撃側で探して null→crash。
- **disc728587（Addison, 07-23）**: 上記を修正するエンジン更新を released。
- **我々への影響**: 我々の cg は **07-18 版**（libcg.so, 07-23修正より前）。ただし **dragapult デッキに
  660/1207 は無い**＝自デッキ無害。ラダー実対戦はサーバ側（修正済み）。skarin agent は内部探索を使わない。
  → **今はリビルド不要**（収束中ドローを退出+枠消費のコストが上回る）。次に dragapult をリロールする際に
  最新エンジンで再ビルドする（disc727094 の前例と同様）。

## 3. クラッシュ回避の落とし穴（disc728519, busyaprime）

- **op.type は生 int**（enum メンバでない）＝`op.type.name` は例外。int と比較すること
  （PLAY=7 ATTACH=8 EVOLVE=9 ABILITY=10 DISCARD=11 RETREAT=12 ATTACK=13 END=14）。
- 初手は select==None＝60枚デッキを返す。不正 index は無視でなく**即死**（game 未完＝敗北扱い）。
- → 我々の `_valid`/`_legal_fallback` ラッパーで対処済み、v038 実測0エラーで機能確認済み。

## 4. 公開エージェント上限スキャン（kernels + LB突合）

- **skarin/Phantom-Dive dragapult = 現時点で最良の採用可能公開エージェント（LB 827.5, SK Arin #735）**。
  現LBで skarin を明確に超える公開エージェントは無い:
  - tomatomato「1300+ Starmie」kernel: 現LB **794**（1300は過去ピーク=減衰）
  - PyJa Mega Lucario v62: 822.1 だが lucario=silver帯最弱archetype(0.342)
  - Roman Rozen「LB950+」: 現711、exp066で棄却済み（silver加重0.5475）
  - Ivan「MultiPly 940」「Improved Probabilistic」: 786、raunakdey(expectimax)765 も既出で不採用
- **disc728168**: ルールベースで **rank 2 / 通常top10 到達者がいる**（"..." のコメント）、Alakazam ルールベース
  で **5位**（sue124/ryotasueyoshi kernel）。＝ルールベースの天井は非常に高い。
- **含意（次レバー）**: skarin 827.5 とルールベース天井(rank2, ~1200+) の差は**パイロット品質**。
  dragapult は最良archetype(0.576)なので、**dragapult パイロット改良に大きな伸びしろ**。
  skarin 自身の改善案(cell15): 2nd Boss's Orders vs 3rd Crushing Hammer / Latias vs 2nd Fezandipiti /
  対Alakazam のダメカン配置スコア調律。→ scout-top（top dragapult パイロットの決定差分を patch）が有効な次実験。

## 5. 運用メモ

- **公開NB締切 Aug 2 23:59 UTC**（通常より1週早い）。skarin は既に公開済み＝採用に問題なし。
  自作NBを公開するなら Aug 2 まで。Strategy 提出に添付した NB は Strategy 締切時に公開される。
- Simulation 締切 8/16、Strategy 9/13。
