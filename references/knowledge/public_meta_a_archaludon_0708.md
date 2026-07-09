# 公開notebook「PTCG Meta A Stable Submit」— Archaludon ex/Cinderace ルールベース分析

- URL/出典: Kaggle公開Notebook「PTCG Meta A Stable Submit」（The Pokémon Company - PTCG AI
  Battle Challenge Simulation）
- 取得日: 2026-07-08
- スコア: 876.9（我々のv014/v013=776-808より上だがメダル圏~1140には届かない中位帯）
- ファイル: `references/raw/public_notebooks/ptcg-meta-a-stable-submit.ipynb`

## 要点: なぜ読む価値があるか
1. **Archaludon exデッキそのもの** — これは我々の実測最弱マッチアップ(v014/Yushinとも
   0.17-0.195)の**中身を直接示す**一次資料。相手の意思決定ロジックが読めるので、
   単なる強さ推定でなく「何を狙われているか」が分かる。
2. **`detect_matchup()`に"hop"（我々のデッキ）専用の対策分岐がある** — Hop's Snorlaxを
   Boss's Ordersで名指しスナイプする等、**我々のデッキを名指しした対策**が既に
   公開レベルで実装されている。向こうの視点から見た我々の急所が分かる。
3. **Crustle対策が非常に作り込まれている**（notebook冒頭に「crustle_attackfix_v1が
   スコア悪化したので安定版に戻した」という経緯あり）— 我々のcrustle戦は逆に得意
   (0.905)なので、直接の転用先ではないが、相手側の失敗パターンとして参考になる。

## デッキ構成（60枚）
Duraludon x4(169) / Archaludon ex x4(190) / Cinderace x4(666) / Relicanth x1(57) /
Basic Metal Energy x11(8) / Ultra Ball x4 / Pokégear 3.0 x4 / Jumbo Ice Cream x4 /
Poké Pad x4 / Explorer's Guidance x4 / Lillie's Determination x4 / Full Metal Lab x4 /
Night Stretcher x3 / Boss's Orders x3 / Hero's Cape x1 / **Judge x1**（ドキュメント外、
ハンド均し用の1枚差し）。

## コンボの核（メタル高速ランプ）
- **Cinderace's Explosiveness**: セットアップで**手札から裏向きでActiveに直接配置**
  （通常のベンチ配置を経ない特殊初期配置）。真の攻撃陣（Duraludon/Archaludon）を
  露出させずに1ターン目を稼ぐ「おとりActive」戦術。
- **Turbo Flare**（Cinderace, {C}1エネで50、山札から基本エネ最大3枚をベンチのポケモンに
  加速）— 実質1ターンで攻撃可能状態まで持っていく高速ランプ。
- **Assemble Alloy**（Archaludon ex, 手札からの進化時に**トラッシュから**メタルエネ
  最大2枚を加速）— 意図的にUltra Ball等でメタルエネをトラッシュに送ってから進化で
  回収する「トラッシュ経由の実質サーチ」設計。ダメージ計算だけでなく**リソース経路**
  まで作り込まれている。
- **Relicanth's Memory Dive**: 進化後ポケモンが**進化前の技を使える**ため、
  Archaludon exでもDuraludonのRaging Hammer（ダメージカウンター比例、1個+10）を撃てる。
  Metal Defenderが通らない相手（Crustle等）への迂回ルートとして機能。
- Full Metal Lab（スタジアム）: 自分のメタルポケモンへのダメージ-30。
  Hero's Cape: +100HP（Archaludon exでHP400到達）。

## 「hop」マッチアップ判定 = 我々のデッキそのもの
```python
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}  # Silicobra/Sandaconda/
                                                                 # Zacian ex/Snorlax/
                                                                 # Rookidee系/Phantump/Trevenant
if ids & HOP_LINE: return "hop"
```
（HOP_LINEは複数のHop's系デッキを包括しており、我々のPhantump/Trevenant/Snorlaxは
その一部として検出される想定。相手はこれを単一の"hop"アーキタイプとして一括りにしている。）

**このマッチアップ専用の対策コード:**
- `opp_max_damage()`で"hop"の最大打点を**220**と仮定（Ice Cream回復判断のしきい値に使う:
  HP>220なら回復スキップ）。
- **Boss's OrdersでHop's Snorlaxを名指しスナイプ**する専用ロジック:
  ```python
  # vs Hop: Boss Snorlax to remove Extra Helpings (+30) ASAP
  ```
  Snorlaxの特性（我々の"Extra Helpings"、打点+30相当）を**相手が明示的に脅威と認識し、
  最優先で除去対象にしている**。2パターンに分岐:
  - Cinderace Active + ベンチにDuraludon系がいる → Turbo FlareでSnorlaxを引き摺り出す
  - Archaludon Active、HP>220、攻撃可能 → Boss's OrdersでSnorlaxを直接指名
- `_ICE_CREAM_HP_THRESHOLD["hop"] = 220` — 我々の最大打点(220想定)ちょうどを生存ラインに
  設定し、それ以上は過剰回復として使わない。

**含意（我々側への示唆）**:
- 相手はこちらのSnorlax（+30ダメージ源）を**最優先撃破目標**と認識している。
  Snorlaxをきっちりベンチ後方に置く/早期にトレードに使い切る等、"名指しされる価値"を
  逆手に取ったブラフ的運用（Snorlaxを目立たせて他の駒を守る）も一案として検討余地。
- 相手はこちらの最大打点を220と見積もっている＝Trevenantの素の130+Revenge時+100=230や
  Choice Band込みの上振れを過小評価している可能性がある。**このギャップ（相手の想定
  220 vs 実際のより高い上振れ）を突く一撃が刺さる可能性**（要検証、実測なし）。
- Archaludon exはHP300(+Cape400)・Metal Defender220と、我々の非exアタッカー（1確殺
  ラインが低い）では正面から時間内に倒しきれない可能性が高い。速攻より「Boss's Orders
  でベンチ低HP个体を刈る」プラン(我々も既存policy_chainで実装済み)が引き続き妥当。

## Crustle対策（相手の失敗経験の記録として参考）
notebook冒頭に「`meta_a_crustle_attackfix_v1`実験がオンラインで悪化したため安定版に
巻き戻した」という記述——**相手も我々同様、crustle戦での試行錯誤に苦戦している**
（我々のcrustle 0.905は相対的に強みであることの傍証）。
- Crustle戦では**Archaludon exへの進化を禁止**（`-10000, "Crustle: don't evolve to ex"`）
  — Crustleに何らかの「ex撃破ボーナス/ex専用ロック」機構があると推測（我々の
  memory `meta-and-leaderboard`の「ラダー上位はanti-ex control」と整合）。
- **Metal Defenderは0ダメージ扱い**（`-5000, "Crustle: Metal Defender does 0"`）—
  Crustleに特定エネルギータイプ/技への完全遮断がある可能性。代わりにRaging
  Hammer（Duraludon側の技、非ex）で迂回。
- 相手のSpiky Energy(id14)装備+2エネ以上のCrustle(345)に対し、フルHPのDuraludonは
  **あえて攻撃せず待つ**——反射ダメージ系の技を警戒していると読める。

## Alakazam脅威モデル（我々が今後遭遇する場合の参考）
`_estimate_alakazam_from_pokes()`: 手札枚数+盤面のAbra/Kadabra/Dudunsparce数から
Powerful Handの床/天井ダメージを算出するfloor/ceiling式（Enriching Energy未使用なら
+3、Fezandipiti ex在場で+3等の細かい補正込み）。手札依存の可変打点デッキへの
定量的脅威評価の実装例として、我々が新規脅威デッキの打点を見積もる際のテンプレに
なりうる。

## 実装スタイルの参考点（コード設計）
- `apply_overrides(obs, opt, score, reason)`: マッチアップ別のハードルールを**通常スコア
  計算の後段でオーバーライドする層**として分離——我々の`_score_card_choice`系と同じ
  「基本スコア→例外オーバーライド」の二層構成。差分は**マッチアップ判定を全スコア関数の
  入口で一度だけ行い、以降は`detect_matchup(obs)`を都度参照**する点（我々のrevenge_policy
  は各所でmatchup依存の分岐を都度書いており、共通化の余地がある）。
- `should_skip_ice_cream()`のようにHPしきい値をマッチアップ別辞書(`_ICE_CREAM_HP_THRESHOLD`)
  に外出ししている——閾値の集中管理は我々のBENCH_DISC/SEARCH_PRIパッチでも踏襲済みの
  パターンと合致。

## 実験候補（未着手）
- 相手のarchaludon想定打点(220)と実際の我々の上振れ（Revenge+Choice Band込み）の
  ギャップを実測し、刺さるなら「Archaludon戦では抑えずに上振れを取りに行く」判断を
  policy_diff的に検証。
- Snorlaxが名指しされる前提で、Snorlaxの配置優先度（ベンチ前方/後方）を
  archaludon対面でのみ変える価値があるか、n≥200で検証。
