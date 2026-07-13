# Knowledge Index

Claude Code はまずこの index を読み、必要なファイルだけ開く。

## Files

| File | Purpose | When to read |
|---|---|---|
| `notebooks.md` | Public notebook 由来の知識 | baseline、特徴量、モデル案を探すとき |
| `discussions.md` | Kaggle discussion 由来の知識（メタ＋**公式 disc708586 sim差分**） | ルール、リーク、CV/LB差分、**setup-bench任意/ability vs skill/退却reset** を確認するとき |
| `external_ideas.md` | 論文、記事、他コンペ由来の知識 | 外部手法やモデル候補を検討するとき |
| `ptcg_strategy.md` | PTCG 代表戦略（prize trade/tempo/archetypes）＋本コンペメタ対応 | 意思決定 diff の解釈、模倣/カウンター設計、レポート語彙 |
| `public_notebooks_0622.md` | 公開ノート3点分析（**5位 Alakazam 実装**・公式 episodes EDA・ルール解説） | Alakazam 対策/評価、動的打点・山札ガード等の piloting 採用、公式 episodes 取得 |
| `engine_source_0703.md` | **公式エンジンソース精査**（Revenge 正確条件=koAttackDamageHop / search は供給仮説で決定的 / ライセンス制約） | pilot の仕様準拠化（v014 exact-window 候補）、Stage 2 belief 設計、カード挙動の答え合わせ |
| `lo_mill_notebook_0702.md` | **公開 LO（Great Tusk mill 4/turn＋Crustle壁＋NZ）1083.6**: 勝利ルート算術比較の操縦、deck+main.py 全公開 | 対 LO 脅威測定（我々のドロー特化が弱点候補）、LO 移植評価、プラン算術 piloting の実装例 |
| `prize_tracking_starmie_0622.md` | **Gold(1250) Starmie**: prize tracking（サイド落ち推定）＋matchup-mode＋検証リーサル探索 | exp015 リーサル探索の偽陽性修正、相手適応、forward-search の hidden info を正す |
| `dragapult_lucariov3_0623.md` | **強 Dragapult ex**（単サイド field を~80%で狩る脅威, exp017 を覆す）／Lucario v3(=v003 同型) | 我々の非ex の脅威評価、deck⊗pilot 再例、spread 耐性 |
| `ptcg_real_strategy_megastarmie_0624.md` | **実 PTCG 戦略**（公式 Mega Starmie ex 攻略＋spread/エネ破壊/prize trade） | gold apex Mega Starmie の操縦ルール化（Jetting スナイプ/Ignition-Nebula で壁貫通/Hammer 妨害/prize trade）|
| `note_tomatomato_worldrank2_0705.md` | **#2 tomatomato 一人称ブログ**（Mega Starmie exデッキ選定理由＋3モードBot設計） | exp022 の「Mega Starmie は deck⊗pilot 不能」結論の裏取り、リーサル探索ROIの型別仮説確認 |
| `public_meta_a_archaludon_0708.md` | **公開Archaludon ex/Cinderaceデッキ**(876.9)。**"hop"(=我々のデッキ)専用対策**（Snorlax名指しBoss狙撃、想定最大打点220前提のIce Cream判断）を実装済み。**追記(0710)**: 後継notebook「BattleCore Compact Agent」(849.6)はロジック完全一致の堅牢化版と確認、新規テクニックなし | archaludon戦(我々最弱0.17-0.195)の相手視点の脅威モデル理解、Snorlax運用の見直し検討。**追記(0712)**: このpilot+自前デッキをv020として我々自身が出荷（exp049、ローカル4.625/6） |
| `../raw/discussions/721010_deck_list_compendium.md` | **disc721010: 15アーキタイプの60枚リスト集（エンジンcardId付き）**——Dragapult3変種/Slowking/Ogerpon3変種/Crustle(Kangaskhanハイブリッド)/Lucario2変種/Alakazam/Starmie-Froslass/Grimmsnarl/Kangaskhan-Bouffalant/Mega Absol Box | ローカル対戦相手の複製材料（未整備アーキタイプの追加）、fine_classifyの分類精緻化（ex_beatdown 2系統問題）、テック採用の辞書（Psyduck=Dusknoir対策、Battle Cage=ベンチ狙撃対策等） |
| `field_reports_rl_and_pilot_0712.md` | **disc717697/721338/713608**: 純RL自己対戦でsilver到達例1件(<2Mパラメータ+カリキュラム)と転移失敗の多数証言／**Boss's Orders・Ultra Ball捨て札は14位でも未解決の難問**（→SEARCH_PRIレシピのv020適用候補）／実トップ1%のsequencing・prize mapping解説 | v020パイロット改良の標的選定、Strategyレポートの第三者証拠、ptcg_strategy.mdの語彙補強 |
| `timing_analysis_field_methods_0712.md` | **disc724362: 30,000試合のタイミング署名分析**——フィールド約半分がルールベース、**トップ勢のほぼ全員が探索不使用**（重モデル+時間フル活用はLB#1のみ）。コメント欄で複数実践者が「value headが優劣を判定できず探索が効かない」と証言＝我々のexp010/014/040と同一機構の独立確認 | Strategyレポートの中心的裏付け（15件の負の結果のフィールド全体での妥当性）、重NN+探索へ回帰しない根拠 |
| `../raw/discussions/724187_pokeforge_postmortem.md` | **disc724187: PokéForgeチームの90レポート級ポストモーテム**。「公開の成熟policyのコピーが自作手法全てに勝った」「調律済みpolicyへの局所パッチは効かない」「模倣一致率<8%でもon-policy強さは保証されない」——**exp050/051の構造的空白則・decision-match≠strength則を独立チームが再確認**。未導入の手法: **CRN(共通乱数)で近縁比較の分散を4.88倍圧縮** | Strategyレポートの第三者裏付け（最重要）、paired evalのn削減余地（CRN導入検討） |
| `field_lb_and_matchup_intel_0713.md` | **disc712621(LB不整合、同一エージェントで最大400pt差)/723591(先攻+10pt、field 91.5%が先攻選択)/716207(Ogerponアビリティ耐性でArchaludon対策説、未実証)/716045(公式6/30更新、draw→timeout負けに変更)/711329(探索中のドロー能力は決定的=clairvoyance注意)** | LB単発値を信用しない根拠強化、v020のIS_FIRST NO-GOの裏取り、v020への潜在脅威監視、探索実装時の注意点 |
| `public_code_sweep_0713.md` | **公開code(kernel)100件スイープ**: pilkwang meta-snapshotシリーズ(大規模field分析、**Archaludonは07-03に一度崩壊→我々の07-12観測で再興=メタ回転の独立確認**、**Starmieが壁/LO系の鋭い天敵**、CRN欠如を独立指摘)/dashimaki360(Day1 Crustle bot=単純action優先度スコアラーのみ=「単純pilot>複雑pilot」の3例目独立確認) | メタ回転周期の裏取り、壁デッキ再導入を避ける根拠、CRN検討の優先度引き上げ、Strategyレポートの「単純さの美徳」節の第三証拠 |

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
- ✅取得済: Simulation discussion 708586（公式ルール vs シミュレータ差分 → `discussions.md` 2026-06-24）。要取得: cabt API docs。

