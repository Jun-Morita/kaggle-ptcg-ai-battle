# 公開ノートブック3点の分析（2026-06-22 取得）

- 取得日: 2026-06-22 / 対象: PTCG AI Battle（Simulation＋Strategy）
- raw: `references/raw/public_notebooks/`（Git管理外）。3rd-party 抽出コードは `.../alakazam/`（Git管理外）。
- **コンプラ**: 本コンペは private sharing 禁止だが、**Kaggle 上で公開された Code/Discussion の利用は許可・推奨**
  （japanese-language-ex のルール解説より）。以下3点は公開ノートなので戦略の参照・採用は合法（出典明記）。

## 1. rule-based-not-psychic-alakazam-best-5th ★最重要
- 大会2日目 LB **5位**の**完全な rule-based Alakazam エージェント**（main.py＋60枚デッキ）。我々が上位で観測した
  Alakazam（THIRD PTCG #2/#3）の公開強実装。
- **コンセプト**: Alakazam「Powerful Hand」= **手札枚数 × 20 ダメージ**。デッキ全体が「攻撃ターンに手札を最大化」
  する設計＝**スケーリング型・単サイド apex**（我々の非ex Trevenant とは別系統）。
- **手札を増やす機関**（攻撃前にこれらで手札を膨らませて打点を作る）:
  Abra/Kadabra 進化ドロー, Dudunsparce「Run Away Draw」+3, **Fezandipiti ex「Flip the Script」+3**,
  サポート Hilda(+1)/Dawn(+2), **Enriching/Rich Energy（貼って+3〜4ドロー）**。
- **採用できる戦術アイデア（洗練された piloting ルール）**:
  - **打点の min/max 見積もり**: 「このターン手札を何枚増やせるか」を数えて Powerful Hand の最大ダメージを事前計算 →
    KO 可能か判定し攻撃/Boss/進化順を決める。＝我々の `_plan_attack`（固定ダメージ）より精緻な**動的打点計算**。
  - **山札枚数ガード(`safe_draws`)**: 「山札残 ≤ サイド残」割れを防ぐためドロー系の使用を制限（デッキアウト自滅回避）。
    勝ち確ターンのみ解除。←我々の方策に無い安全弁。
  - **条件付きテック**: Battle Cage(対 Dragapult系), Psyduck(対 Duskull), Shaymin(対 水/Ogerpon/N's Darumaka),
    Genesect+Lucky Helmet(相手 ACE SPEC 未使用時), **Enhanced Hammer×3（相手の Mist/Rock 特殊エネを剥がす）**。
  - **進化優先度**: Alakazam(active)→Kadabra→Dudunsparce→Alakazam(bench)。
- **我々への脅威＝実測で否定（exp016, n=40）**: **v008(charmq 非ex) vs Alakazam = 0.900**(36-4)で圧倒。
  懸念した Enhanced Hammer × 我々の Mist Energy は**無害**（剥がすには手札消費＝Powerful Hand 打点低下の自己矛盾。
  我々の機関＋Choice Band の安定打点が単サイド・レースに勝つ）。lucario_v2(ex) vs Alakazam=0.475＝ex の中堅カウンター。
  → **Alakazam は我々の脅威でない**。非ex apex の優位を補強。
- **採用方針**: ①**評価プールに Alakazam を追加**（トップ archetype の対戦相手をローカルに獲得＝評価忠実度↑）。
  ②動的打点計算・山札ガード・条件テックの考え方を我々の方策/レポートに取り込む。③そのまま提出はしない
  （独創性ゼロ＝Strategy 不利、ただし Simulation では合法）。
- deck ids: 741×4(Abra) 742×4(Kadabra) 743×3(Alakazam) 305×3(Dunsparce) 66×2(Dudunsparce) 140(Fezandipiti ex)
  142(Genesect) 858(Psyduck) 343(Shaymin) 1152×4(Poké Pad) 1086×4(Buddy-Buddy Poffin) 1079×3(Rare Candy)
  1097(Night Stretcher) 1129(Sacred Ash) 1156×3(Lucky Helmet) 1081×3(Enhanced Hammer) 1182×2(Boss's Orders)
  1231×4(Dawn) 1225×4(Hilda) 1264×4(Battle Cage) 5×2(Basic P Energy) 19×4(Telepath P) 13(Enriching Energy, ACE SPEC)。

## 2. japanese-language-ex
- 公式 **Mega Lucario ex** rule-based サンプルの日本語訳＋解説（＝我々の `lucario_v2` baseline と同等の方策・デッキ）。
  新規の方策的価値は小（既知）。出典: kiyotah の公式サンプル。
- **価値ある中身＝ルール解説**: チーム最大5人, **private sharing 禁止（チーム外/SNS/知人との戦略共有は違反）**,
  **公開(Code/Discussion)での共有は OK**, チームマージ期限=終了1週前(本コンペ 2026-08-10)。
  → 本リポの公開ノート利用は合法、の根拠。
- 補足: 「ポケカは不完全情報ゲーム＝ポーカーAI の先行研究が参考になる」との示唆（[[external_ideas]] 候補）。

## 3. ptcg-official-top-episodes-detailed-eda-ja
- **公式 top episodes を読む EDA 方法論**（チーム別勝敗・対面・試合長・頻出カード/アクション・勝者偏りカード）。
  ＝我々の `exp011/analyze.py` の拡張版。ローカルにファイル無し（51M, JSON 破損）だが**手がかりが有用**:
  - **公式 episodes データセット**: `pokemon-tcg-ai-battle-episodes-index` ＋日別 `pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`
    ＝per-submission API より**バルクな上位リプレイ源**。`/meta-watch` の取得元を公式 episodes index に拡張する候補。
  - カード名/画像は公式カード一覧CSV＋カード画像PDFから取得。

## 出典
- rule-based Alakazam (5th): https://www.kaggle.com (rule-based-not-psychic-alakazam-best-5th)
- 元アイデア「why-alakazam-is-a-good-baseline」: heiseimikiko
- 公式 Mega Lucario ex サンプル: kiyotah / Beginner Guide: ichigoe
- 公式 top episodes EDA: 公式 episodes データセット前提

## 2026-06-25: 「Pokémon TCG Deck Transformer Training」(public, GPU) — 評価済み・不採用
- raw: `references/raw/public_notebooks/pok-mon-tcg-deck-transformer-training.ipynb`（gitignore）。26セル/88k字。
- 中身＝**デッキ構築支援ツール**（操縦には無関係）:
  1. `PrefixNextCardModel`: デッキ(bag-of-cards mean-pool, ID emb + 属性feature hybrid)→次/隠し1枚を予測（デッキ補完・leave-one-out・ACE SPEC 候補比較）。
  2. `MatchupWinRateModel`: my/opp 両デッキを同 DeckEncoder で符号化→`[my,opp,my*opp,my-opp]`→MLP→勝率(BCE)。**＝デッキリストのみから勝率予測**。
  3. 候補を rule/win/gen score で rerank。日次 dataset `pokemon-tcg-ai-battle-episodes-YYYY-MM-DD` から60枚抽出（`steps[1][p].action` len60）。
- **不採用の理由（我々の確立事実に紐づく）**:
  1. デッキ不足でない＝トップの decklist を完全複製済み（charmq非ex＝#2 Mogja と一致）。補完提案に価値なし。
  2. **win-rate model はデッキのみで勝率予測＝操縦を無視**。だが「勝敗を決めるのは操縦」を5-6回実証（[[meta-and-leaderboard]] deck⊗pilot / Mogja 同一デッキ +200LB / take-when-legal）。最重要因子を構造的に取りこぼす。
  3. マッチアップは meta-watch の**実ラダー W-L** の方が高精度（μ600/メタ回転も捕捉）。学習代理は劣化。
  4. 我々の律速＝**pilotability**（exp020 Tinkaton）。共起/fit 最適化はそこに効かない。GPU+学習コストに見合わず。
  5. 転用部品（battle JSON→60枚抽出）は decode_replay.py/meta_watch で保有済。新情報は日次バルク dataset だが既知。
- コンプラ: 公開ノート＝学習参照OK（実行不要）。**結論: よく出来たデッキ/勝率ツールだが我々には不採用**。

## 2026-06-26: 公開ノート4本（archeops×2 / multiply-940 / mega-lucario-v62）+ Neutralization Zone 検証
- raw: `references/raw/public_notebooks/{archeops-draw, japanese-archeops-devolve, multiply-agent-best-940-lb, ptcg-mega-lucario-ex-v62}.ipynb`。**採用ゼロ・intel 多**。
- **ptcg-mega-lucario-ex-v62**（Mega Lucario ex, rule-based）: 我々の方法論を**独立に裏付け** — ①matchup tech は全て **gated**（相手盤面に counter カードがある時だけ発火＝zero-downside）②**moderate 値**（"高値は over-commit して価値ある KO を逃す"＝exp023 RB=50/exp025 と一致）③**進化前を先に潰す**（Riolu→Lucario, Snover→Mega Abomasnow +950, Abra/Kadabra→Alakazam +400）＝exp025「Duraludon を Archaludon 前に」と同原理。opponent intel。
- **multiply-agent-best-940-lb**: 実 Search API（beam3 + MCTS15, 1.5s）を正用も **LB 940 < v006 1086**＝探索≤ヒューリスティック再確認。不採用。
- **archeops×2**（退化軸: げんしのつばさ→いわおとし100で進化前KO）: honest negative（PUBLIC 3-9/6-9）。学び＝化石2進化が遅い＝pilotability 律速／CV-LB 乖離／過ドローでデッキ切れ。Tinkaton/TR 結論を補強。
- **★Neutralization Zone(1247)(exp026)**: Stadium/ACE SPEC「非ルールポケが相手ex/Vダメージ無効」。charmq の Legacy Energy(12)→NZ 差し替え(n=100): archaludon 0.12→0.16/ex 0.69→0.73/dragapult 0.12→0.18（小・反転せず）だが **crustle 0.79→0.59(−0.20)**/mirror −0.04 ＝**不採用**。理由: NZ は Stadium で自 Postwick(+30) を上書き＋uptime低／非ex(Duraludon/Drakloak)が貫通／非ex相手に dead card。net 中立〜微負。出典 `workspace/exp026_neutral/`。

## 追記 2026-07-02: mega-pokemon-reinforcement-ai-battle.ipynb
- タイトルに "Reinforcement" とあるが**学習要素ゼロの純ルールベース Mega Lucario**（全文検査: torch/報酬/Q値/更新則なし。"trained to" は比喩）。
- 中身は lucario_v2 同クラスの手書きスコア（prize優先ターゲット、エネ×150、弱点2倍、hand<6ドロー、Boss条件付き）。我々の v009-v012 が既に上位互換。スコア実績表示なし。**採用なし**。
- 教訓: 公開NBのタイトル/説明は実装と乖離しうる。コード検査を先に。

## 追記 2026-07-03: pokemon-metall.ipynb（955.6, Archaludon+Cinderace metal-tempo）
- デッキ: Archaludon ex×4/Duraludon×4/Cinderace×4 + Full Metal Lab×4 + Explorer's×4（8=鋼エネ11）。
  ShumpeiNomura 系（元#1, 現在は top14 から後退）アーキタイプの公開版。
- **対 Hop 専用モード搭載＝我々のアーキタイプへのカウンター実装**:
  detect_matchup で HOP_LINE 検出 → (a) **Boss's Orders で我々の Snorlax を釣り出して排除**
  （Cinderace Turbo Flare で狙撃 / 「Extra Helpings +30 を早期除去」と明記）、
  (b) 対 hop 想定最大打点 220 と見て Archaludon HP>220 を維持する回復ゲート。
  → 我々の Snorlax がベンチ負債である傍証（v009 規律の裏付け）。
- **本番でも探索を使用**（MultiPly 系 beam search）: 公式 search API、CAND=6/depth40/margin ゲート/
  時間予算/例外時ヒューリスティックフォールバック。`obs.search_begin_input`（本番 obs に常設の
  シリアライズ状態文字列）経由 → **公開エージェントにも本番探索層が普及し始めている**。
  我々の v013 guard と同族だが、彼らは「良さそうなら上書き」、我々は「全K破滅時のみ拒否権」でより保守的。
- 含意: (1) 公開により **Archaludon+対Hop テックが我々の μ帯(800-950)に増える恐れ**
  ＝我々の最悪マッチ(0.165-0.175)のシェア上昇リスク。/meta-watch で Archaludon シェア要監視。
  (2) 静的な per-matchup 打点上限テーブルは、我々の guard が動的・正確に計算するものの下位互換＝採用不要。
