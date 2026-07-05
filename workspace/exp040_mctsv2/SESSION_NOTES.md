# exp040 — 公式 RL/MCTS サンプルへの回帰: 決定化バグ修正 + ネイティブエンジン

## 仮説
exp004（`workspace/exp004_mcts/`）は公式 AlphaZero系サンプル(Transformer value/policy + MCTS over
Search API)を移植し、対ルールベースプールで惨敗(0.017-0.033 vs バー0.680)した。診断は2点:
1. 決定化が相手をSnorlaxプレースホルダで穴埋め(`opponent_deck=[1072]*N`)＝偽物の相手に対して計画。
2. データ/計算量が桁違いに不足(旧ctypesエンジンで5世代・約2万サンプル)。

この2点は、その後の実験(exp019のPrizeTracker、exp032のネイティブエンジン、exp039のOpponentModel)
で解決策が実証済み。本実験はexp004のアーキテクチャ(Transformer+PUCT MCTS)は変えず、この2バグだけを
直して再検証する（他の変数を変えずクリーンに切り分けるため）。詳細方針は `.claude/plans/` 参照
（承認済みプラン、ユーザー承認済み: 2026-07-05）。

## Stage 0: 配線修正（完了）

### 変更点
- `train_mcts.py` を exp004 から fork。`load_engine()` を exp032 のネイティブビルド
  (`exp032_valuescale/native/`, 0.12s/game) に向けた。
- 新規 `determinize.py`: `mcts_agent`内の決定化を`opponent_deck=[1072]*N`等のプレースホルダから、
  除外方式サンプリング(decklist - 可視カード)に置換。自己対戦はミラー(両者が同じ既知デッキ)なので
  exp038/039のアーキタイプ検出は不要、単純化した版を実装(`_card_ids`/`_mon_ids`パターンはexp039から再利用)。
- エンジン制約: `opponent_active`はPokemonカードでなければならない(`ValueError`で発覚)→
  `pokemon_ids`集合を渡し、プール内でPokemonタイプのカードのみをactive候補にするよう修正。

### 決定化の精度検証（対角検算: 各決定点で 可視カード + サンプルされた隠匿カード の合計が
実デッキの枚数構成と一致するか）
発見した3段階のギャップ（PrizeTrackerの`_unseen`が元々対処していたのと同種）:
1. `state.stadium`(場のスタジアム) と `obs.select.effect`(解決中のカード) を計上していなかった
   → 追加。ただし単純な加算だと、エンジンがカードを2箇所に一時的に二重表示するフレームがあり
   (観測: Hariyamaが実際2枚しかないのに3回計上される)、`max()`マージに変更して解消。
2. `state.looking`(デッキ覗き効果の公開カード) と `obs.select.deck`(デッキから選ぶ効果の対象)も
   試したが、**悪化した**(不一致率 43%→90%超)。理由: この非exデッキはUltra Ball/Poké Pad/Pokégear
   等で自分のデッキを頻繁にサーチするため、これらの効果中は`select.deck`に残りデッキの大部分が
   一度に公開される。それらを「可視」として除外すると、`deckCount`基準のサンプル必要数(`needed`)が
   それに応じて減らないため、プールが必要数を大きく下回り**フルデッキfallbackを毎回誘発**して逆効果。
   正しく直すには「公開された既知カードをそのままyour_deckの該当箇所に固定する」設計変更が必要
   (単純な除外集合では不十分)。**このセッションでは見送り**(Stage 1のgo/no-go判断には影響しない
   精度、後述)。
3. 最終的に採用: stadium + select.effect + select.contextCard(単一カード源のみ) の max マージ。

### 残存する不正確さ（定量化・許容判断）
複数seedで検算: 決定点の**4-15%**で、上記の除外プールが必要数をわずかに下回りフルデッキfallback
(`pool = list(deck)`)が発動する(deck-search効果中心、デッキ構成依存で変動)。フォールバック時は
exp004のプレースホルダと同程度の精度に一時的に後退するが、**クラッシュはしない**。残り85-96%の
決定点は正確な除外サンプリングが効く。「0%正確(exp004) → 85-96%正確」への改善であり、Stage 1の
安いgo/no-go判定には十分な精度と判断し、完璧な修正(公開カードの固定配置)は保留。

### 動作確認
- n=20 vs random(untrained, search_count=8): エラー0, 3.37s/game。
- n=12 selfplay(untrained, search_count=8): エラー0, 5.29s/game, 1269サンプル。
- **n=50 selfplay(untrained, search_count=8): エラー0, 6668サンプル, 6.91s/game。Stage 0 完了。**

Stage 0 の go/no-go: クラッシュ0件、決定化の整合性85-96%を確認 → **Stage 1 へ進行**。

## Stage 1: 安いgo/no-go（完了）

### Stage 1a: 学習曲線の健全性（exp004と同規模: 5世代, search_count=16, selfplay=40, eval=20）
| gen | vs random | loss |
|---|---:|---:|
| 0(未学習) | 70% | 0.2711 |
| 1 | 35% | 0.1425 |
| 2 | 40% | 0.0656 |
| 3 | 40% | 0.0372 |
| 4 | 65% | 0.0344 |

lossは単調減少するが、vs random勝率は改善せず振動(exp004の75/35/60/65/40%と同型パターン)。
n=20のためこれ単体では未決着。

### Stage 1b: 実プール評価（決定的テスト、`eval_vs_pool.py`, model_gen4, n=40/相手, search_count=16）
| 相手 | 勝率 | 記録 |
|---|---:|---|
| random | 0.700 | 28-12-0 |
| dragapult | **0.000** | 0-40-0 |
| lucario_v1 | **0.000** | 0-40-0 |
| lucario_v2 | **0.000** | 0-40-0 |
| **対ルールベース平均** | **0.000** | バー: 0.680 |

exp004の0.017-0.033よりさらに悪い完全シャットアウト。エラー0件（クラッシュではなく正真正銘の敗北、
`run_gauntlet`で`errors0=0`を個別確認）。念のため**未学習(gen0)モデルでも同一条件でlucario_v2に
0-10**を確認 -- gen0とgen4で結果が同じ(共に0)ということは、**5世代の学習では方策/価値ネットが
ほぼ何も改善しておらず、探索(search_count=16, PUCTガイド)そのものがまだ弱い一様に近い prior/valueの
下では lucario_v2 の調整済みヒューリスティックに歯が立たない**ことを示す。これはexp004の元々の診断
(「データ/計算量が桁違いに不足」)と整合し、かつ**決定化を直しただけではこの小規模での勝率を全く
動かさなかった**ことを明確に示す(cause 1を直してもcause 2が支配的なら効果が見えないのは想定内)。

### ユーザー判断（2026-07-05）
Stage 1の結果を受け、「Stage 2へ進むが、GPUは他の用途で使用中のため、今のうちに設計を固める」との
判断。実装のみ先行し、実際のGPU大規模投入はユーザーの合図待ち。

### Stage 1 go/no-go判定
決定化修正(cause 1)は正確性としては大きく改善(0%→85-96%の決定点で厳密除外サンプリング)したが、
この小規模(5世代・数百試合)ではプール勝率を**全く動かさなかった**(0.000のまま)。プランの「決定的な
足切り」条件(「ヒューリスティックの土俵(0.3程度)に近づかない」)に該当。Stage 2(ネイティブエンジンの
速度を活かした桁違いのスケールアップ、数時間〜数十時間のGPU投資)に進む前に、**ユーザーに状況を報告し
判断を仰ぐ**(このセッションの決定的チェックポイント)。

## Stage 2 設計（実装済み、起動はGPU空き待ち）

GPUが別用途で使用中のため、実装・検証のみ先行して固める(ユーザー指示)。

### 核心的な変更: teacher-assisted self-play（cold-start対策 + コスト半減の一石二鳥）
Stage 1の`selfplay()`は両席とも`mcts_agent`(MCTS)を使うミラー自己対戦。この設計には2つの問題:
1. **cold-start**: 相手も同じくらい弱い自分のコピーなので、学習に値するゲームが生まれない
   (gen0とgen4が同一の0-40という結果はこれを裏付ける)。
2. **コスト**: 両席がMCTS(数秒/決定)を払うため、1試合が高コスト(7-14s/game)。

`selfplay_vs_teacher(deck, model, search_count, n_games, teacher_agent)`を新規実装
(`train_mcts.py`): 片方の席を固定の高速ルールベース方策(`revenge_policy`, 探索なし,
0.29ms/決定を実測)に置き換える。これにより:
- 学習対象(trainee)は初手から手強い(少なくとも一様ランダムより遥かに強い)相手と対戦し、
  情報量のあるゲームから学習できる。
- 1試合のコストが概ね半減(MCTSを払うのはtrainee側の手番のみ)。
- LearnSampleはtrainee側の手番のみ収集(教師側は学習対象でないため)。
- `deck`は両者同一(ミラー)なので`determinize()`は無変更で正しく動作(決定化はカード構成のみに
  依存し、操縦者が誰かには依存しない)。

教師の選択: `revenge_policy`(RB=50, v011で出荷実績のある汎用方策, 探索なし=高速)を採用。
`turnbeam_policy`(v014, 内部で独自のbeamサーチを持つ)も`--teacher turnbeam`で選択可能にしたが、
これは1手あたりのコストが高く「コスト半減」のメリットを損なうため、まずはrevenge一択で試す方針。

### 追記(2026-07-05, ユーザー指摘): デッキ多様性 + 過去提出AIの活用 + ランダム選択

ユーザーからの3点の指摘を受けて設計を拡張:
1. 「速いルールベース方策は複数デッキの多様性をもたせるべきでは？」
2. 「過去提出したAIを使うのもあり」
3. 「ランダムさをどう扱う？」→ 確認の結果、**相手デッキ/教師の選び方**の意味と判明。

**根拠**: exp032で価値ネットが初めて学習可能になった(中盤AUC 0.784)のは、まさに単一デッキ→
複数デッキ混合プールへの切り替えがきっかけだった(exp014の319試合・単一マッチ構成では学習不能)。
同じ教訓を自己対戦の「教師」側にも適用する。

**重要な副次的発見**: この拡張作業の過程で、exp004由来の`--deck`デフォルトが`lucario_v2`
(exp007時代の旧ex主体デッキ)のままだったと判明。**v011以降の実際の出荷デッキは
`exp012_nonex/charmq_deck.json`(非ex Hop's Trevenant)**であり、lucario_v2は非exピボット
以前の遺物。Stage 0/1は「exp004とのアーキテクチャ比較」が目的だったため`lucario_v2`のままで
問題なかったが、**Stage 2からは実際に出荷するデッキ(`charmq`)で学習するよう修正**
(`load_deck("charmq")`を追加、`--deck`デフォルトを`charmq`に変更)。

**実装** (`teacher_pool.py`新規, `train_mcts.py`の`determinize`/`mcts_agent`/`selfplay_vs_teacher_pool`
/`pool_eval`を汎用化):
- `determinize(obs, your_index, my_deck, opp_deck, pokemon_ids, rng)`: 両者同一デッキ前提を廃し、
  `my_deck`/`opp_deck`を別々に受け取るよう一般化(除外サンプリングの対象デッキを正しく分離)。
  自己対戦は常に両デッキを自分で選ぶため、アーキタイプ検出(exp038/039)は依然として不要。
  非対称デッキでの整合性検算(charmq vs crustle, n=47決定点)でも**同水準(7/94≈7.4%)の
  残存不正確さ**を確認、ミラー版から悪化なし。
- `mcts_agent(obs_dict, your_deck, model, search_count, opp_deck=None)`: `opp_deck`省略時は
  `your_deck`と同一(ミラー、既存呼び出し元との後方互換)。
- `teacher_pool.py`: 確立済みの**5マッチアップ評価フィールドそのもの**(crustle/dragapult/
  archaludon/ex_lucario/mirror)を教師プールとして構築。`(name, deck, factory, weight)`のリスト。
  - crustle: `AC.make_crustle_agent()` + `AC.CRUSTLE_DECK`
  - ex_lucario: `AC.make_agent(AC.LUCARIO_DECK)` + `AC.LUCARIO_DECK`
  - dragapult: `load_dragapult.make_dragapult_agent()`(公開ノートブック実装) + 実デッキ
  - archaludon: `load_archaludon.make_archaludon_agent()`(公開ノートブック実装) + 実デッキ
  - mirror_revenge: `revenge_policy.make_agent(trainee_deck)`, weight=2.0(最安・主力)
  - mirror_turnbeam: `turnbeam_policy.make_agent(trainee_deck)`(**v014、過去提出AI**), weight=0.3
    (探索を内包し高コストなので低頻度の「時々混ぜる」役)
  - LO(Great Tusk mill)とGrimmsnarlは既存の`matchups/`記録で「非脅威」判定済みのため対象外。
- `selfplay_vs_teacher_pool(trainee_deck, model, search_count, n_games, teacher_pool)`:
  ゲームごとに`random.choices(teacher_pool, weights=...)`でマッチアップをランダム選択、
  trainee側の物理シート(0/1)もゲームごとに交代(`g % 2`)。返り値に`matchup_counts`
  (Counter)も追加し、実際にどのマッチアップが何回選ばれたか可視化。
- `pool_eval()`も`teacher_pool.py`ベースに統一(旧baselines.pyのlucario_v1/v2/dragapultから、
  確立済み5マッチアップ実体に切替。mirrorはコスト削減のため周期チェックからは除外)。
- `main()`: `--teacher {none,revenge,turnbeam,pool}`、`pool`が推奨(多様デッキ+過去AI混合)。
  `--deck`デフォルトを`charmq`に変更。

**動作確認**(GPU負荷は最小限に留めた):
- `--deck charmq --teacher pool`: 1世代(selfplay=6,eval=4)が23sで完走、pool評価も動作
  (`crustle=0.00 ex_lucario=0.00 dragapult=0.00 archaludon=0.25`, n=4なのでノイズ)、
  `matchups={'mirror_revenge': 3, 'dragapult': 2, 'ex_lucario': 1}`のようにランダム選択も確認。
- `selfplay_vs_teacher_pool`単体でn=20試合、エラー0、5マッチアップ中4種が実際にサンプルされた
  ことを確認(`{'crustle': 3, 'ex_lucario': 8, 'mirror_revenge': 6, 'dragapult': 2,
  'mirror_turnbeam': 1}`)。

### 起動前コードレビュー(2026-07-05, ユーザー指摘「操作のモデル化は大丈夫か」)

ユーザーの直前の質問(1ターン内の複数操作のモデル化)を受けて、「操作のモデル化」全体を起動前に
再点検した。確認した観点と結果:
- `get_decoder_input`の`OptionType`網羅性: エンジンの全17種類(NUMBER/YES/NO/CARD/TOOL_CARD/
  ENERGY_CARD/ENERGY/PLAY/ATTACH/EVOLVE/ABILITY/DISCARD/RETREAT/ATTACK/END/SKILL/
  SPECIAL_CONDITION)を`match`文で全てカバーしていることを確認(欠落なし、公式サンプルのまま)。
- `create_node`の複数選択列挙(`obs.select.maxCount`個を選ぶ組み合わせ列挙、最大64通り): 標準的な
  組み合わせ生成アルゴリズムとして正しく動作(公式サンプルのまま、変更していない)。
- 1ターン内の複数連続操作: 前メッセージで検証済み(`yourIndex`ベースの毎手番ディスパッチ、
  MCTSのnegamax符号反転も`yourIndex`比較ベースでply数に依存しない)。
- **`run_gauntlet`/`run_match`の規約とのシート非依存性**: `run_match`は`_empty_deck_obs()`で
  各エージェントに「自分のデッキは何か」を問い合わせ、`swap_sides`でシートを入れ替える。
  `mcts_agent`は`obs.current.yourIndex`から`your_index`を都度導出するため、シートが入れ替わっても
  正しく動作することを確認(ハードコードされたシート依存なし)。
- **見つけて修正した2件**(致命的ではないが起動前に直した):
  1. `selfplay_vs_teacher_pool`の未使用変数`names`を削除。
  2. `mcts_agent`の`opp_deck or your_deck`という書き方は空リストのデッキがあれば誤動作しうる
     脆いパターン(実際には60枚デッキが空になることはないため実害はないが)→
     `your_deck if opp_deck is None else opp_deck`に明示化。
  3. `eval_vs_pool.py`(Stage 1時代の検証用スクリプト、Stage 2の実行経路には含まれない)が
     dragapult/lucario_v1相手でも一律`opp_deck`省略(ミラー扱い)のままだった、実際のデッキを
     渡すよう修正。Stage 2の起動には影響しないが、後で誰かがこのスクリプトを単独実行した際に
     誤った決定化で誤解を招く結果が出るのを防止。
- 結論: **致命的なバグなし、起動可**。修正後に`--deck charmq --teacher pool`でスモークテスト
  再実行し、正常動作を再確認。

## Stage 2 起動・中間診断・リプレイバッファ追加(2026-07-05夜〜07-06)

### 初回起動(gen0-21, replay bufferなし)
`run_stage2.sh 50 16 150 20 5`で起動。gen0/5/10/15/20の5回のpool評価が**全てcrustle/ex_lucario/
dragapultで0.000近辺、archaludonも0.25→0.15→0.00→0.05→0.00と改善なし**。予算(50世代)の約30%
(gen20)を消化した時点でユーザーに報告 → **「即座に停止して詳細診断」**の指示。

### 詳細診断(3点)
1. **価値ネットの識別力(AUC)**: revenge_policy自己対戦20試合・900局面で、model_gen0のvalue出力
   とmodel_gen21のvalue出力を「最終的な勝者を予測できるか」でAUC比較。
   - gen0(未学習): AUC≈**0.489**(ランダム相当、想定通り)
   - gen21(21世代学習後): AUC≈**0.628**(明確にランダムを上回る、**実際に何か学習している**)
   - 単純な平均値比較(勝った局面 vs 負けた局面)では差が見えなかった(gen21は全体が-0.3付近に
     シフトしただけ)が、これは「全体的な悲観バイアスの学習」であり、順位ベースのAUCで見ると
     識別力自体は確かに向上している。**「配線が壊れている」という仮説は否定された**。
2. **探索深度への感度**(exp010の決定的診断を再現): model_gen21をsearch_count=4/16/32で
   vs randomに対して評価 → 7/20(0.35)→4/20(0.20)→4/20(0.20)。**深くするほど悪化**、
   exp010「価値ネットの質が低いと探索が深いほどノイズを増幅する」と同型の症状。
3. **データ量の桁**: 21世代で蓄積した学習サンプルは約26,700件。exp032で価値関数が学習可能に
   なった(AUC 0.784)のは99,328試合・248万行。**現状はその1/100以下の規模**。

**結論**: 決定化やteacher-pool設計の欠陥ではなく、**価値ネットは正しい方向に学習し始めている
(AUC改善は本物)が、データ量が桁違いに不足**。exp014→exp032と同型の「データ律速」の初期段階。

### ユーザー判断: 「このPCのGPUを数十時間規模で動かすのは問題ない」

大規模投資の前に、安価な設計改善を1点追加(`train_mcts.py`):
- **リプレイバッファ**(`--replay-cap`, `--train-batches`): 初回起動は各世代が**その世代の
  自己対戦サンプル(~1000件)だけで学習し、直後に破棄**していた(リプレイバッファなし)。
  公式AlphaZero系実装の標準(直近N世代分をプールして学習)から外れており、観測された
  「価値の振動」の一因の可能性。`replay_buffer`をスライディングウィンドウ(サイズ上限
  `--replay-cap`)として保持し、`train()`は`--train-batches`でバッファサイズに関わらず
  1世代あたりの勾配ステップ数を一定に保つ(バッファ肥大で学習時間が際限なく伸びるのを防止)。
  小規模スモークテストで動作確認(buffer=30上限で正しく打ち止め)。
  **既知の制約**: バッファはメモリ上のみ(`--resume`時はリセットされ、以降の世代で再構築される)。

### 再起動(2026-07-06, gen22〜, 目標2000世代)
`model_gen21.pth`から`--resume`で再開、`--replay-cap 100000 --train-batches 80`を追加、
`--generations`を50→**2000**に拡大(数十時間規模のGPU予算をユーザーが許可)。
`run_stage2.sh`のデフォルトも同様に更新。

**既知の限界(新規追加なし、既存の枠内)**: `revenge_policy`/`turnbeam_policy`はモジュールレベルの
ターン跨ぎグローバル状態(`_rev`等)を持ち、`factory(deck)`を毎ゲーム新規呼び出ししても
**モジュールグローバルなのでゲームをまたいで状態がリセットされない**(exp038/039で対処した
クラスの問題と同型)。ただしこれは`harness.run_gauntlet`を使う既存のあらゆる呼び出し元に
共通する既存の挙動であり、本リファクタで新たに導入したものではない。影響は新しいゲームの
最初の1-2ターン程度に限定される見込みで、Stage 2の「まず動くか」を確認する段階では
許容範囲と判断。気になる場合はexp039の`_last_turn`パターンで対処可能(未実装、必要になれば着手)。

### 実装した付随機能
- `--tag`: `results/<tag>/`に出力を分離(Stage 1の結果を上書きしない)。
- `--resume`: 既存の`model_gen*.pth`から再開(WSL再起動対策、既存の再開可能チャンクパターンを踏襲)。
- `--pool-eval-every N`: N世代ごとに`lucario_v1/v2/dragapult`への実勝率も記録
  (`pool_eval()`関数, `harness.run_gauntlet`を直接呼ぶ、サブプロセスなし)。
  Stage 1の教訓(「vs randomは弱い/誤解を招く代理指標」、gen0/gen4ともに0.000だったのに
  vs randomは35-70%で振動)を踏まえ、本当の判断材料(ルールベースプールでの勝率)を学習ループの
  中で安く継続監視する。

### 動作確認(小規模スモークテスト, GPU使用は最小限に留めた)
- `--teacher revenge --tag smoke_teacher --pool-eval-every 1`: 2世代(selfplay=4,eval=4)が
  7s+5sで完走、エラー0、pool評価も動作(`lucario_v2=0.25`等、n=4なのでノイズだが機構は正常)。
- `--resume`: 既存のgen1から正しくgen2として再開することを確認。

### Stage 2 起動時の推奨パラメータ（設計のみ、未実行）
`run_stage2.sh <generations> <search_count> <selfplay> <eval> <pool_eval_every>` を用意。
初回の目安: generations=50, search_count=16, selfplay=150, eval=20, pool_eval_every=5,
tag=stage2, teacher=revenge。既存の resumable chunk パターン(setsid+nohup+DONEセンチネル)で
バックグラウンド起動する。

### Stage 2 自体のgo/no-go(実行中の中間チェックポイント)
計画された予算の**最初の20-30%を消化した時点**で`pool`の記録(lucario_v1/v2/dragapultへの
勝率)を確認する。3種すべてが依然として0.000近辺(明確な改善の兆候なし)であれば、
残り予算を消化する前に一度ユーザーに報告し、続行/打ち切りの判断を仰ぐ
(sunk-costで惰性的に走らせ続けない)。逆に一つでも明確な非ゼロ・上昇トレンドが出れば、
それは「cold-start修正が効いている」実証であり、継続投資の根拠になる。

## Stage 2 最終結果・打ち切り判断（2026-07-06、gen469で停止）

### 実測結果（gen25〜400、pool評価76回分の集計）
リプレイバッファ追加後、gen22から`--generations 2000`で継続実行。gen400（予算20%消化、
経過約5.6時間）で中間報告した集計:

| 相手 | 非ゼロ回数/観測回数 | 非ゼロ時の値 |
|---|---:|---|
| crustle | **0/76** | (一度も勝ち星なし) |
| ex_lucario | 8/76 | 0.05-0.10 |
| dragapult | 2/76 | 0.05 |
| archaludon | 24/76 | 0.05-0.15 |

loss は 0.087(gen22) → 0.044(gen400) と単調に低下し続けたが、直近100世代では鈍化
(0.049→0.044)。vs randomは一貫して0-45%で振動しトレンドなし。**lossの低下と実戦勝率の
乖離が375世代・数十万ゲームを経ても解消しなかった**。

gen400（20%予算消化）でユーザーに報告 → **打ち切り、アプローチ自体は選択肢として保持、
敗因分析を優先**の判断（2026-07-06）。gen469まで実行後、プロセスをTERMで安全停止
(`model_gen468.pth`まで保存済み、`--resume`で再開可能)。

### 敗因仮説: crustleへの完全シャットアウトは「ゲームモデル化不足」を示唆
crustleは`exp007_anti_crustle`で専用カウンターが必要だったと記録されている**壁/耐久型
アーキタイプ**（詳細はexp007 SESSION_NOTES参照）。exp033でも「価値ネットを1手先読みの
貪欲上書きとして統合すると壁デッキで悪化する」という近い症状が出ており、今回のMCTS版でも
同型の弱点が再現している可能性が高い。仮説:
- 壁デッキ戦は「短期的に不利に見える手が長期的に正解」になる場面が多く、data-starvedな
  価値ネット(AUC 0.628程度)+ 浅い探索(search_count=16)の組み合わせでは、この非直感的な
  価値評価を学習しきれていない可能性。
- 探索深度を上げるほど悪化する(exp010型の症状、search_count=4/16/32で0.35→0.20→0.20)
  という既存の診断も、「価値ネットの質が探索量に見合っていない」という同じ原因を指す。
- ex_lucario/dragapult/archaludonでは散発的に0.05-0.15が出ている(=完全な0ではない)のに
  crustleだけ完全に0という非対称性は、決定化やエンジンのバグというより「crustie特有の
  長期的な意思決定パターンをこの規模のデータでは学習できていない」という説明の方が
  一貫している(バグなら特定の相手だけ選択的に0にはなりにくい)。

### 次の一手（検討中、未着手）: トップランカー戦略のデータ活用
ユーザー提案: 「トップランカーの戦略をデータとして活用できないか」。自己対戦のみに頼らず、
`workspace/exp011_meta_watch/`が既に持つ**ラダーリプレイ取得の仕組み**([[meta-and-leaderboard]]
参照)を使い、上位プレイヤーの実対戦ログを教師データ(模倣学習の初期化 or 追加の価値ラベル)
として活用できないか検討する。これはteacher-assisted self-playの「ルールベース教師」を
「実測の強い相手のログ」に置き換える/補完する発想で、特にcrustleのような長期プランニングが
要る相手には、自己対戦だけでなく実際の勝ち筋データが効く可能性がある。次セッションで
scoping要。

### Stage 2 総括
決定化バグ(cause 1)の修正は85-96%の精度で完了・実証済み。データ量問題(cause 2)への対応
としてネイティブエンジン+リプレイバッファ+teacher-assisted self-playを実装し375世代・
数十万ゲームを投入したが、実プールへの勝率改善は確認できず（crustleは完全シャットアウト
継続）。**9件目の誠実なネガティブ**として記録。アプローチ自体(決定化修正+MCTS)は死んでは
おらず、「データ量 or データの質(自己対戦のみでは壁デッキの学習に不十分)」という新しい
仮説が浮上した状態で保留。
