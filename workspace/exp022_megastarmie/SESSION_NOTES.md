# exp022_megastarmie — SESSION NOTES

目的: トップ #2 tomatomato(LB1290) の **Mega Starmie ex + Mega Froslass ex** デッキの feasibility 調査
＋「操縦のコツ」研究。Path B（前回分析: #3 Mogja は我々と同一デッキ=差は操縦／#2 は非exを狩る別apex）。

## デッキ（`/extract-deck 53881664`, 183/183 games, exact 60）
- ポケモン: Snorunt(860)×4 → **Mega Froslass ex(861)×3** / Staryu(1030)×4 → **Mega Starmie ex(1031)×3**。**全て Stage-1（基本→Mega）＝操縦可能ライン**（Tinkaton S2 と違う）。
- エネ: 基本水(3)×9 / Mist×1 / Legacy×1 / Ignition×1。
- トレーナー: Buddy-Buddy Poffin×4 / Energy Search×4 / Salvatore×4 / Lillie's Determination×4 / Pokégear×3 /
  Wally's Compassion×3 / Switch×2 / Mega Signal×2 / Boss×2 / Hilda×2 / Gravity Mountain×2 / Night Stretcher×1 / Black Belt's Training×1。

## カード機構（EN_Card_Data）— 操縦の鍵
- **Mega Starmie ex**(HP330, weak {L}):
  - Jetting Blow: **{W} 1エネ = 120 + ベンチ1体に50**（超効率スプレッド, 計170）。
  - Nebula Beam: ●●● 3エネ = **210, 弱点/抵抗＋相手アクティブの効果を無視**＝**Crustle の Safeguard を貫通**（ex 無効化を抜ける唯一手）。
- **Mega Froslass ex**(HP310, weak {M}):
  - Resentful Refrain: {W} = **50×相手手札枚数**（大型手札を罰する）。
  - Absolute Snow: {W}●● 3エネ = 150 + 相手ねむり。

## feasibility 実測（generic 方策＝card 知識なしでビルド, built artifact, 0 err）
| Mega Starmie (generic pilot) vs | wr | tomatomato(熟練) |
|---|---|---|
| **v006 我々の非ex** | **0.825**(33-7) | 0.76 |
| lucario_ex | 0.475 | 0.71 |
| Crustle | **0.10** | **1.00** |
| dragapult | 0.50 | 0.64 |

## 中間結論（★強い GO）
- **デッキ floor が既に強い**: generic 操縦でも**我々の非ex を 0.825 で狩る**＝現メタ(非ex多)への構造的カウンター。Tinkaton(0.00)/弱Dragapult と全く違う。
- **弱点は純粋に操縦ギャップ**: Crustle 0.10（熟練1.00）/ ex 0.475（0.71）。原因＝generic は Mega の攻撃モデルを持たず、
  **Nebula Beam(Safeguard貫通)を使えない**＝Crustle に ex 攻撃が無効化されて負ける。これが「操縦のコツ」の正体。
- → **専用 pilot patch（exp012 と同型: `_base_attack` モデル＋`_plan_attack`）で Crustle/ex を引き上げられる見込み**。特に **vs 壁は Nebula Beam 強制**。

## 第1次 pilot patch（`starmie_policy.py`）→ ★退行（重要な学び）
- `_base_attack` モデル＋`_plan_attack`（vs 壁=ex攻撃 d=0→Nebula Beam 強制）＋水弱点＋search 優先度を実装。
- 結果（built artifact, 0 err）: ex 0.35 / **Crustle 0.05**(generic 0.10 より悪化) / dragapult 0.35(0.50 より悪化)。
  ＝**明示モデルが base の generic 攻撃選択より下手**＝net 退行。
- **診断**: vs Crustle で**1ゲームあたり攻撃プランは僅か ~2回**（40ゲームで77）。原因＝
  壁相手は ex 攻撃が全て d=0 で、**3エネ Mega Starmie を組めず Nebula Beam に到達できない**→何もできず棒立ちでデッキアウト負け。
- **結論（操縦の真の律速）**: 問題は attack model でなく**複数ターンの setup/sequencing**。
  壁を倒す唯一手 Nebula Beam(210, Safeguard貫通)には**3エネを1体の Mega に集中**する必要があり、
  汎用のエネ付け/進化ロジックはそれを志向しない。tomatomato(Crustle 1.00)はこの段取りを操縦でやっている。

## feasibility 最終判定
- **デッキ = 強い GO**: generic floor で既に非ex 0.825（現メタの構造的カウンター, ミラー弱点を回避）。Stage-1 で crash-safe。
- **操縦 = 多段イテレーション要**: 競技力には「**狙ったMegaにエネ集中→大型Nebula Beamを通す**」setup レイヤーが必須。
  第1次パッチ（攻撃モデルのみ）では不足。floor の重み付き field ≈0.556 < v006 0.66（ex0.475/Crustle0.10/dragapult0.50 が足を引く）。
  ceiling は tomatomato ≈0.75 field＝**操縦で 0.556→0.75 を詰める研究課題**（ユーザー狙いの「操縦のコツ」研究の好題材）。

## setup/sequencing レイヤー（第2次）→ ★トレードオフのみ、クラックせず
- エネ集中 override（Mega Starmie を3エネへ寄せる／壁相手は加点）を追加。
- 診断（patch版, vs Crustle n=40）: MAIN 260手中 **Mega Starmie 盤面131手だが3エネ到達は僅か16手**、Nebula 計画31/Jetting 84、**0-20**。
  ＝①3エネ到達が遅い ②**Nebula Beam 210 < Hero's Cape Crustle 250HP＋回復**で、通っても倒し切れない。
- 変種比較（built artifact, n=24, ノイズ±0.10 込み）:
  | 変種 | ex | Crustle | dragapult | (vs 非ex 既知) |
  |---|---|---|---|---|
  | generic(無パッチ) | 0.35 | 0.10 | 0.50 | 0.825 |
  | full pilot(攻撃モデル+plan) | 0.33 | 0.08 | 0.46 | — |
  | min(エネ集中のみ) | **0.17** | **0.21** | 0.38 | — |
  - **エネ集中は壁を改善(0.10→0.21)するが aggro(ex/dragapult)を悪化**＝**matchup を取り合うだけでトータル改善せず**。
  - 私の明示 attack-model/plan は base の汎用攻撃選択より下手（ex 0.35→0.33, dragapult 0.50→0.46）。

## ★最終判定（誠実な負・ただしデッキは良い）
- **デッキ floor は強い**（非ex 0.825）が、**我々の generic+heuristic-patch では競技ピロットに届かない**。
  どの override も1つの matchup を上げ別を下げるだけ。floor 重み付き field ≈0.55 < v006 0.66。**提出候補にならない**。
- tomatomato の ceiling（ex0.71/Crustle1.00/非ex0.76/dragapult0.64 ≈0.75 field）との差＝**操縦の段取り**:
  「**正しいタイミングで1体に集中→Nebula Beam を OHKO 窓で通す＋壁の回復を上回る運び**」。これは静的ヒューリスティックで表現困難。
- **deck⊗pilot の再確認（5例目）**: 今回は floor が強い点が新しい（Tinkaton 0.00 と違う）が、**ceiling を引き出す操縦が我々の枠組みの外**。
- レポート価値大: 「**同じデッキでも操縦で field 0.55↔0.75。操縦の knack＝多ターンのエネ段取り＋大技の窓合わせ**」を定量化＝
  ユーザー狙いの「操縦研究」の核心的データ。Strategy の Model独創性/deck⊗pilot 章に直結。

## ★操縦研究：tomatomato リプレイ精読（`decode_replay.py`）→ 操縦の knack を抽出
4勝の Crustle戦＋ex戦をデコード（生 replay の option を意味解釈）。抽出した「操縦のコツ」:
1. **Mega Starmie に即進化**（active で turn1-2 には Mega）。基本を抱えず素早く進化。
2. **Jetting Blow が主力**（{W}1エネ=120＋ベンチ50スプレッド, **毎ターン**撃つ）。Nebula Beam ではない。
3. **エネは active 攻撃役に集中**（0→1→2→3e）、ベンチ Mega は2eで待機。
4. **Mega を複数並べ、Retreat で充電済み攻撃役を active に維持**（盤面を厚く）。
5. **Nebula Beam(3エネ210)は大型 HP への burst finisher のみ**。
- 攻撃ID確定: Jetting Blow=1487({W}1, 120+50bench) / Nebula Beam=1488(3, 210, 効果無視) / Resentful Refrain=1240 / Absolute Snow=1241。

## ルール化の再挑戦 → ★ヒューリスティックでは捕捉できず（4変種すべて generic 未満）
- pilot3（Jetting 主力化＋壁 d=0 バグ除去）: ex 0.325 / Crustle **0.05**(2-38) / dragapult 0.375。なお generic floor は ex0.35/Crustle0.10。
- **4変種（attack-model / energy-only / Jetting主力 / 組合せ）すべて generic の汎用攻撃選択を下回る**。
  → 操縦の knack は**逐次的・文脈依存**（進化/集中/退却/技選択を盤面で動的に判断）で、**静的な per-option スコアでは表現できない**。
- 補足: ローカル `AC.make_crustle_agent()` は Hero's Cape250+回復+ex無効化＝**ラダーの Crustle(tomatomato 4-0)より硬い**。Crustle 0.05-0.10 は局所的に過小。

## ★RL/学習の判定（公式 RL+MCTS ノート精読＋過去4ネガティブ）
- 公式 `reinforcement-learning-and-mcts-sample-code.ipynb` ＝ **我々の exp004/008/010/014 と同一の AlphaZero(Transformer value+policy)+MCTS**。
  しかも **determinization は相手を Snorlax(1072) で穴埋め**（`opponent_deck=[1072]*N`）＝**exp008 で 5倍劣ると実証した placeholder 相手そのもの**。
  → **フル self-play RL/MCTS は非推奨**（value ネットが中盤を読めない exp014 AUC<0.70 ＝ 4本目までの結論を公式コードが追認）。
- **ただし本件は新条件**: 「**1つの強い expert(tomatomato 183戦)・1デッキ**」の模倣（BC）は、exp010 の多教師BC(0.22)と質的に違う:
  ① 逐次・文脈依存の knack を**学習なら捕捉し得る**（静的ルールの限界を超える）。② BC は **action 予測のみ＝value ネット不要**で exp014 の中盤value問題を**回避**。
  ③ 公式ノートが **特徴抽出器(get_encoder/decoder_input) を無償提供**。④ リスク: 誤差累積で exp010 は 0.22。focused BC で改善余地はあるが上限はあり得る。

## ★focused 行動クローン（BC）→ 5本目の学習ネガティブ（誠実・機構付き）
- データ: tomatomato 183戦の MAIN 単選択判断 **2,752 decisions / 17,410 option-rows / 28次元**（`bc_dataset.py`）。
- 学習: listwise ranker（小MLP, GPU, `bc_train.py`）。**val action-match = 0.49**（random 0.22／我々heuristic ~0.28）＝**2.2倍の実信号**、
  train≈val で**過学習なし**（exp014 の rich embedding train0.999 と対照的にクリーン）。
- agent化: hybrid（MAIN piloting=BC / 機構選択=generic, `bc_agent.py`）→ **vs field（n=40, 0err）**:
  | BC agent vs | wr | generic floor |
  |---|---|---|
  | v006 非ex | 0.45 | **0.825** |
  | lucario_ex | 0.33 | 0.475 |
  | Crustle | 0.08 | 0.10 |
  | dragapult | 0.23 | 0.50 |
- **全マッチで generic floor 未満**＝**典型的 BC 誤差累積**（exp010 再演）: 1手49%一致＝51%は不一致→~15手で累積し、
  tomatomato が訪れない state にドリフト。加えて**分布シフト**（BC は対ラダー相手で学習、評価は我々baseline＝OOD）。
  DAgger で補正したいが**expert(tomatomato)に問い合わせ不可**＝原理的に不可。

## ★最終結論（操縦研究の総括）— レポートの目玉
**「操縦」がこのコンペ最大のレバー**だが（#3 Mogja は同一デッキで 1284, ミラー0.68 vs 我々0.40／#2 Mega-ex floor が我々を0.825で狩る）、
**その knack を AI に落とす3経路すべてが generic floor を超えられない**:
1. **静的ヒューリスティック**（exp022 pilot1-3＋エネ集中, 4変種）= 全て generic 未満。knack は逐次・文脈依存で per-option score では表現不能。
2. **focused BC（強expert 1人・1デッキ模倣）** = action-match 0.49 でも誤差累積で agent は generic 未満。
3. **self-play RL/MCTS** = exp004/008/010/014 の4ネガ。公式ノートも**placeholder相手(Snorlax穴埋め)**＝exp008 で5倍劣ると実証済の欠陥を踏襲。
→ **中位資源では「強いデッキ＋汎用方策＋クラッシュ安全」が achievable ceiling。操縦の上積みは学習でも探索でも届かない**（機構: 中盤value不能＋誤差累積＋逐次文脈性）。
- 提出は v006/v007 維持。Mega Starmie は**強いが我々の枠組みでは ceiling を引けない**（deck⊗pilot 5例目, floor が強い新型）。

## ★RLのアプローチを変えて再挑戦：自己模倣学習 SIL（value-free）→ これも負（6本目）
- 設計（過去の失敗機構から逆算, `sil_iterate.py`）: value不使用／BC warm-start／**自己対戦の勝ち試合の手だけ**で再学習／
  相手は**フィールド(v006/ex/Crustle/dragapult)**＝ミラー回避／ε=0.15 探索。＝BC の誤差累積・分布シフト、exp010 の cold-start崩壊、exp014 の value不能を**すべて回避する設計**。
- 結果（warm-start BC→2 iter, eval n=40 ノイズ込み）:
  | | v006 | ex | crustle | dragapult | collect_wr |
  |---|---|---|---|---|---|
  | iter0(BC) | 0.725 | 0.175 | 0.075 | 0.25 | — |
  | iter1 | 0.500 | 0.175 | 0.025 | 0.25 | 0.215 |
  | iter2 | 0.450 | 0.175 | 0.000 | 0.30 | 0.200 |
  - **改善せず、むしろ低下**。collect_wr ~0.20（240+戦の堅い信号）＝policy がフィールドに ~80% 負け→**勝ち試合が少なく/まぐれ**→強化信号が弱い・偏る。

## ★★ 核心診断：ボトルネックは「学習アルゴリズム」でなく「表現力」
- BC も SIL も **action-match の上限 0.49** を継承（28次元 hand-craft 特徴）。**我々の特徴/方策クラスが expert の決定関数を表現しきれていない**。
- リッチ特徴（公式 encoder の全カード埋め込み）で action-match を上げられる可能性はあるが、**exp014 で value 側は train0.999 過学習**＝同じ轍のリスク大。
- ＝**4経路（heuristic / BC / SIL / self-play MCTS）すべてが generic floor 未満**。学習の「アルゴリズム」を変えても突破できず、残る理論レバーは「表現（特徴）」のみ＝高リスク。

## 総合結論（不変・むしろ強化）
中位資源では **「強デッキ＋汎用方策＋クラッシュ安全」が achievable ceiling**。操縦の上積みは
**heuristic でも BC でも SIL でも self-play RL でも探索でも届かない**（機構: 中盤value不能＋BC誤差累積＋逐次文脈性＋表現力不足）。
Mega Starmie は強いが我々の枠組みで ceiling を引けない（提出は v006/v007 維持）。

## ★辞書(k-NN)BC ＋ リッチ特徴 BC（ユーザー提案「expert の手を辞書化／表現を変える」）→ 同じ天井
- **辞書 k-NN**（`knn_bc.py`, expert の手を圧縮せず検索）: action-match k1 0.384 / k3 0.407 / k5 0.425 ＝**MLP 0.49 より低い**。
  診断: **val state の 86% が near-identical な expert state を持つ**（中央距離0.083）のに再現は0.42＝
  **特徴上は同一の局面で expert の手が58%食い違う**＝我々の特徴が捨てている情報（手札中身/Mega別エネ分布等）で決めている。
- **リッチ特徴 BC**（`bc_rich.py`, 56次元＝手札カード数＋Mega エネ分布＋相手詳細を追加）: **val 0.45 で頭打ち**, train 0.50→0.66＝**過学習のみ**（exp014 再現）。
  ＝missing 情報を encode しても**val 改善せず**。天井 ~0.49 は **モデルクラスでも粗い特徴でもなく**、2752 判断では expert の手が ~50% 超えて予測不能（データ不足＋一部は本質的＝good な選択肢が複数）。
- 「複数作って RL データ化」: 表現を変えても 2752 で過学習＝**データ量が律速**だが、各トップは別 deck⊗pilot（exp010 多教師BC=0.22 と同型）＝
  我々がスクレイプできる範囲では**巨大データ＋大モデル(公式Transformer)が要り資源外**。

## ★★ 最終総括（操縦研究, 完全版）
**「操縦」がコンペ最大レバー**だが、**5系統すべてが achievable ceiling（generic floor）を超えられない**:
heuristic(4変種) / BC(MLP 0.49) / **辞書k-NN(0.42)** / **リッチ特徴BC(過学習)** / SIL(value-free, 低下) / self-play MCTS(4ネガ)。
**機構**: ①中盤 value 不能(exp014) ②BC 誤差累積＋分布シフト ③逐次・文脈依存で静的scoreに乗らない ④**action 自体が ~50% 超予測不能**(データ不足＋複数 good 手)。
→ 中位資源では **「強デッキ＋汎用方策＋クラッシュ安全」が achievable ceiling**。提出 v006/v007 維持。これが Strategy レポート中核。

## 再利用資産
- `decode_replay.py`／`bc_dataset.py`+`bc_train.py`+`bc_agent.py`／`sil_iterate.py`／`knn_bc.py`／`bc_rich.py`（BC/SIL/k-NN/リッチ 一式, GPU）。

## 関連
- #3 Mogja J = 我々と完全同一デッキで 1284（差は100%操縦, ミラー0.68 vs 我々0.40）→ [[meta-and-leaderboard]]。
- deck⊗pilot 密結合の好例（generic floor は強いが熟練 pilot で +大幅）。
