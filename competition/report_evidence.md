# Strategy Report — Evidence Ledger (data + sources)

レポート執筆用の数値・事実の台帳。`report_draft.md` の各章に対応。数値は実測（ローカル harness は
先後入替, n=各記載）。出典は `workspace/expNNN/SESSION_NOTES.md`, `submit/SUBMISSIONS.md`,
`workspace/exp011_meta_watch/results/*.json`。最終更新 2026-06-24（exp018/019/020/021 反映）。

---

## A. 競技/環境（§2）
- cabt エンジン（kaggle-environments）。部分観測・確率的・**可変異種の行動空間**（agent は option index の list を返す）。
- レーティング = TrueSkill 系 N(μ,σ²), μ0=600, 勝敗のみ, **最新2提出が最終評価**, ライブ継続対戦, ~10分/試合, 5提出/日。
- 提出 = `main.py`(top-level) + `deck.csv` + `cg/` の tar.gz。
- カードプール 1267枚（うち ex 121, 非ex HP≥100 アタッカー 469）。

## B. 評価基盤・方法論（§3）
- ローカル harness（exp001）: `run_gauntlet`, 先後入替でバイアス相殺, 例外=反則負け, ~10ms/game。
- **リプレイ解析パイプライン**（exp011）:
  - `analyze.py <subId>`: 自提出のラダー全リプレイDL→相手アーキタイプ別 W-L。
  - `top_meta.py <subId>`: 上位プレイヤーの自デッキ＋相手構成＋戦績。
  - `extract_deck.py <subId>`: 任意選手の**正確な60枚**を最頻デッキとして復元（`/extract-deck` skill）。
  - DL: `kaggle competitions episodes/replay`（raw は gitignore）。

## C. 中心的発見: 相手モデルが探索の価値を決める（§4, exp008）
| 設定 | 勝率 | 備考 |
|---|---|---|
| 素朴 1手読み(exp003) | 0.21–0.27 | placeholder 相手で有害 |
| cold-start AlphaZero(exp004) | ~0.03 | デモ規模 |
| BC+MCTS(exp006) | 0.233 | ルールベース(0.68)未満 |
| **placeholder determinization** | **0.083** | 相手を Snorlax で穴埋め＝偽の相手に最適化 |
| **belief 接地 determinization** | **0.417** | 相手を実デッキからサンプリング（**5倍**） |
- belief 時の探索内 相手手数 50 vs placeholder 33。PIMC vs Dragapult 0.667（素ルールベース超え）。
- 公開上位 notebook は探索 API を誤署名で呼び実質無効＝**誰も探索を正しく使えていない**（差別化点）。

## D. 動的メタの実測（§5）— リプレイ駆動
### メタ回転タイムライン
| 日付 | 上位/field メタ | 根拠 |
|---|---|---|
| 06-18 | **Crustle anti-ex 壁コントロール** | v001 が Crustle に 0/4（ex 攻撃39回全0ダメ） |
| 06-20 AM | **Lucario-ex ビート復権**（field 57%） | v003 の46試合: 下表 |
| 06-20 PM | **非ex アタッカーへ収束**（上位） | charmq#4・tk#8 が同型非ex, Crustle が上位から消滅 |

### v003 の field 構成（46試合, sub 53846234, 06-20 AM）
| 相手 | 我々 W-L | 勝率 | 占有 |
|---|---|---|---|
| lucario_ex | 8-18 | 0.31 | 57% |
| crustle_control | 8-1 | 0.89 | 20% |
| mixed_ex | 5-1 | 0.83 | 13% |
| non_ex_attackers | 3-1 | 0.75 | 9% |
| dragapult | 1-0 | 1.0 | 2% |
→ v003(ex デッキ) が **ex ミラーに負け越し**, 1123→975 低下の正体。

### トップランカー プロファイル（top_meta.py）
| 選手(LB) | デッキ | 主要戦績 |
|---|---|---|
| **charmq #4** (1259→1232) | 非ex Hop's Trevenant | vs lucario_ex **0.69**(11-5) / vs crustle **0.70**(7-3) / mixed 0.71 |
| **tk #8** (1207) | **同型** 非ex | vs lucario_ex **0.92**(12-1) / 非exミラー 0.75(6-2) / **Crustle 遭遇0** |
| **shu #13** (1166) | 洗練 Lucario-ex | vs crustle **0.80**(8-2) / ex ミラー 0.58 / **vs 非ex 0.43**(3-4) |
- 三すくみ: 非ex →(勝つ)→ {ex ビート, Crustle 壁}；ex ビート → 壁；壁 → ex ビート。**頂点=非ex**。
- 頂点の機序: ①単サイド(ex は2-3)でサイドレース有利 ②非exダメージが ex限定 Safeguard を貫通。

## E. 我々の提出と LB 推移（§5, §6）
| 版 | 中身 | LB | 実戦/ローカル |
|---|---|---|---|
| v001 | Lucario+安全性 | 841.8 | Crustle に全敗 |
| v002 | belief PIMC | 820.1 | ミラー飽和ラダーで非ミラー優位活きず |
| v003 | anti-Crustle カウンター | 1123→~1100→975 | Crustle 0.10→0.55; 回転後 ex ミラー負け |
| v004 | Crustle 壁(汎用方策) | 742→853 | 実戦 ex 0.62, crustle ミラー 0.60, 全体0.59 |
| v005 | Crustle 専用方策 | 857 | 汎用 v004 にミラーで負け(5-19) |
| **v006** | **非ex apex(charmq複製,汎用)** | **1121.4(最高)** | 実戦 ex 0.70/crustle 0.80/非exミラー0.60/全体0.68 |
| **v007** | **非ex 専用方策** | PENDING | ミラー(vs generic) **0.775**/ex 0.725/crustle 0.625 |
- 追従の物語: v003(anti-Crustle)→v004(壁)→v006(非ex apex)→v007(ミラー強化)。
- eligible(最新2)= **{v007, v006}**（v007 主力, v006 が Crustle カバー）。

### マッチアップ行列（ローカル, n=30–40, 先後入替）
| エージェント | vs lucario_v2(ex) | vs Crustle | vs 非ex(mirror) | vs dragapult |
|---|---|---|---|---|
| v003 (ex anti-Crustle) | 0.467 | ~0.50 | 0.40 | — |
| v004 (Crustle 汎用) | 0.867 | (mirror 0.79 vs v005) | — | 1.00 / iono **0.0** |
| **v006 (非ex 汎用)** | 0.667 | **0.833** | 0.60 | **0.10** |
| **v007 (非ex 専用)** | **0.725** | 0.625 | **0.775**(vs generic) | 0.10 |

## F. デッキ解説（§5, Deck Score 20%）— 非ex Hop's Trevenant（charmq の60枚を複製）
- **ポケモン**: Hop's Phantump×4 → **Hop's Trevenant×2**(HP140, Stage1) / **Hop's Snorlax×2**(HP150, basic) /
  Dunsparce×4 → **Dudunsparce×3**(HP140, Stage1)。全て**非ex=単サイド**。
- **キー特性/攻撃**:
  - **Extra Helpings**(Hop's Snorlax, ベンチ常在): 自分の Hop's ポケモンの攻撃に **+30**（重複不可）。
  - **Run Away Draw**(Dudunsparce): 1ターン1回, 3枚ドロー後この個体を山に戻す＝**ドロー機関**。
  - Hop's Trevenant **Horrifying Revenge**(1エネ, 30, Psychic; リベンジでKO返し)＝主力, boost で 90。
  - Trevenant **Corner**(3エネ, 90, 相手リトリート不可)。
  - Hop's Snorlax **Dynamic Press**(3エネ, 140, 自傷80)＝大型KO用（普段はベンチで特性供給）。
- **道具/サポート**: **Hop's Choice Band×4**(Hop's に +30 & コスト-1) / Boss's Orders×2(狙撃) /
  Lillie's Determination×4 / Buddy-Buddy Poffin×4 / Pokégear×4 / Poké Pad×4 / Hop's Bag×3 /
  Night Stretcher×3 / Colress's Tenacity×2 / Brock's Scouting×2 / Postwick×4(スタジアム)。
- **エネ**: Mist×4 / Telepath Psychic×4 / **Legacy×1**(取られるサイド-1)。
- コンセプト: **単サイドで ex にレース勝ち＋Safeguard 貫通**。Extra Helpings で全体打点を底上げ, Choice Band で KO ライン到達, Boss's Orders で詰め。

## G. 操縦の発見（§5b, Model 独創性）
- 汎用 lucario_v2 方策は非exデッキで `_base_attack` が全 None → `_plan_attack` が **plan を作らない** →
  Boss's Orders(plan.target≥1で発動)・リトリート/switch(plan.attacker≥1)・対象選択・KO認識が**全停止**。
- パッチ（exp012 `nonex_policy.py` PATCH_SRC）: `_base_attack` に非ex攻撃モデル(Extra Helpings+30, Choice Band+30/コスト-1)
  ＋`_plan_attack` の弱点タイプ修正(Trevenant/Phantump=Psychic, 他=Colorless)。下流が一斉作動。
- 結果: **ミラー(同一デッキ smart vs generic) 0.775**(31-9), ex 0.667→0.725。Crustle 0.833→0.625(壁相手の Boss's Orders 過用が副作用)。
- 教訓: **rewrite せず1モジュール注入**が安全（full-rewrite の専用 Crustle 方策 v005 は汎用 v004 にミラーで負けた）。

## H. 安定性・運用（§6, Model 安定性軸）
- クラッシュ安全ラッパー（例外/不正手→合法フォールバック）。全テストで **0エラー**。
- 手番速度 **0.02–0.16s/手**（タイムアウト無縁）。探索版 PIMC は ~30s で非実用。
- 運用サイクル: 週次 `analyze.py` でメタ確認 → 回転があればカウンター更新＆提出, なければ静観。

## I. 学習系の3重ネガティブ（§7, 誠実さ・再現性, exp010）
- BC(多教師, greedy): 平均 0.222（crustle 0.375/lucario 0.167/dragapult 0.125）= 誤差累積, warm-start 素材。
- **Phase 2**(beat-the-field, 8世代): loss↓ だが eval 崩壊（gen7 対 Lucario 0.0, self-play 対 Crustle 0-16）。
- **Phase 3**(ミラー特化, 固定相手+経験リプレイ+崩壊復帰 gating): 崩壊抑止できたが **0.31 天井**（目標0.55, v003 0.47）。
- **探索量スケーリング（決定的）**: ミラー勝率 search 24→48→96 = 0.31→0.19→**0.13**（速度0.05-0.18s/手）。
  良い value なら探索は単調に効く → **value ネット不良**で深探索が誤推定を増幅。
- 核心: BC greedy 0.17 → +belief-MCTS(search24) 0.31 ＝ **価値は学習でなく推論時の探索＋belief**。
- 原理的次手（未実施, 長期）: stock vs stock の大量対戦で value 較正 → MCTS。 → **exp014 で実行・棄却（下記）**。

## I2. オフライン value 較正の決定的ネガティブ（§7, exp014）
- データ: トップランカー8 subs（charmq の対戦相手）の **319試合**, 実勝敗ラベル `rewards:[-1,1]`,
  **試合単位 holdout 20%**（leakage なし）。25,563 記録（choice 19,619）, value バランス win13,424/loss12,139。
  `dataset_builder.py` が1リプレイから4種教師（BC action / 実勝敗 value / デッキ / 相手カード頻度=determinization 事前分布）を抽出。
- トップ戦略（実戦記録）: charmq 非ex apex = vs lucario_ex **0.69** / crustle_control **0.70** / ex-mix 0.67-0.75（~0.70）。
  刈っているフィールドは依然 ex 主体（Mega Lucario ex 支配 + Iono Bellibolt ex + Abomasnow ex + Alakazam）。上位同士は ~0.5（対称）。
- go/no-go（中盤 進行0.4-0.6 の勝敗 AUC ≥ 0.70）:
  | 特徴量 | train AUC | test AUC | 中盤AUC |
  |---|---|---|---|
  | strategy-lens スカラー17 | 0.912 | 0.688 | **0.637** |
  | ＋手札中身+自他盤面 カードレベル embedding | 0.999 | 0.684 | **0.585** |
  | baseline (prize_diff 単独) | — | 0.688 | — |
  - 進行段階別(rich): 序盤0.66 / 中盤0.58 / **終盤0.80**。
- 結論: **2特徴量とも中盤 AUC<0.70 で一致**。カードレベルは train 0.999＝丸暗記で汎化せず（6デッキ319試合）。
  prize 差が唯一の汎化信号。終盤可・中盤不能 ＝ **exp010「探索増で悪化」を機構的に説明**（中盤の無情報 value を MCTS が増幅）。
  → deep-RL/MCTS は経験的に上限。出典: `workspace/exp014_rl_offline/{SESSION_NOTES.md, results/value_calib*.json}`。

## I3. 正確 near-terminal 探索も超えない（§7, exp015）
- 仮説: exp014「終盤 AUC 0.80」→ 学習せず**エンジンの正確な前方探索を自ターン限定**で使い、v008 の取りこぼし KO/リーサルを拾う。
  自ターンは相手が動かず手札も可視＝ほぼ完全情報（exp008 の placeholder 問題が無関係）。
- `tactical_search.py`（v008 router を base に1手先オーバーライド, 保守的, クラッシュ安全）+ `eval_tactical.py`（先後入替）。
- 結果（ミラー＝同一 charmq デッキで純粋に探索の寄与）:
  | 変種 | ミラー vs v008 | vs ex | v008 vs ex(ref) |
  |---|---|---|---|
  | プライズ最大化 (n40) | 0.400 | 0.625 | 0.625 |
  | リーサル限定・1サンプル (n100) | 0.410 | 0.750 | 0.780 |
  | リーサル・K=5 頑健 (n60) | 0.467 | 0.667 | 0.783 |
- 結論: 3変種とも **≤0.47＝v008 を超えない**。原因 ①自ターンも自分のドローで非決定的(偽陽性リーサル)
  ②貪欲な near-terminal 最適化が多ターン狙撃プランを破壊 ③v008 が既にリーサルを十分拾う(`sc=50000`)。
  → **学習(exp014)・探索(exp015)の両系統を実証で潰した**。出典: `workspace/exp015_tactical/SESSION_NOTES.md`。

## K. 規律パッチ＝ミラー天井突破（§6, exp018, v009）
- 仮説検証「トップは相手アーキを読んで方策を変える」→ **棄却**。トップ非ex選手のリプレイを相手アーキ別に分解
  (`analyze_adaptation.py`): 我々との手一致率は全マッチで**一様 ~0.28**（読み替えなら不均一になるはず）。
  彼らの優位は **prize-liability 規律**＝ベンチ数が少ない（~3 vs 我々 4+）＝差し出すサイドKO標的が少ない。
- base 方策は非ex を全て score 20000 で並べる過剰展開。`discipline_policy.py`（PATCH_SRC, v009）:
  Trevenant ライン上限・ベンチ1枠維持・冗長エンジン抑制・サイド負け時のみ +1 アタッカー・armed 1エネに無駄エネ禁止・
  **Crustle 壁相手は自己無効化**（壁には展開が要る）。
- 結果（built artifact, **n=200 ペア**, err0）: **非exミラー vs 無規律 build = 0.550**（110-88-2, 95%CI が 0.50 を除外）。
  フィールド回帰なし（ex +0.00, Crustle −0.01[v008の0.938 は n=16 のfluke, 実~0.72], dragapult +0.05）＝**v008 の上位互換**。
- 誠実な但し書き: **ラダーのミラーは ~0.40 のまま**（実相手が我々を上回って操縦）。ゲインは実在するが小＝
  「**操縦規律が最後のレバーで、ほぼ飽和**」が結論。出典: `workspace/exp018_adaptive/{SESSION_NOTES.md, eval_mirror.py, eval_compare.py}`。

## L. レバー網羅閉鎖＋メタ内位置（§8, exp019-021, 0624）
- **デッキ革新（exp020, Tinkaton アンチミラー）**: カードプールに強い未活用1エネ非ex（Tinkaton 240, Ceruledge 220…）。
  Tinkaton "Windup Swing"(240−60×相手activeエネ)＝構造的アンチミラー武器を試作 → **vs v009 ミラー 0.000**（0-20）。
  原因＝**S2 ライン(Tinkatink→Rare Candy→Tinkaton)が generic pilot で組めず、S1 apex にレースで完敗**。
  ＝**pilotability(ラインの速さ・複雑さ)が律速**＝我々が S1 非ex を選ぶ理由。出典: `exp020_deckinnov/SESSION_NOTES.md`。
- **セットアップ規律（exp021）**: 公式 disc708586＝setup ベンチは任意(minCount==0→部分集合可)。我々の pilot は全 basic 並べ。
  cap で制限 → **我々のデッキでは no-op**（basic-light＝setup で平均 1.41 体, >3体提示 0%）。
  n=200 ペア: ミラー cap2 0.515/cap3 0.480/cap4 0.495＝**全て 0.50±1SE 内**。＝レバーは basic-heavy デッキ専用。出典: `exp021_setupbench/{SESSION_NOTES.md, diag_setupbench.py}`。
- **検証リーサル finisher（exp019）**: prize-aware（サイド落ち推定で前方探索の山を正す）。ミラー n=200 = 0.530（有意差なし, fired 23/試合）。
  exp015 の prize-blind は有害, prize-aware は無害だが我々の1KO/ターン型には不要。出典: `exp019_finisher/SESSION_NOTES.md`。
- **強 Dragapult ex の脅威（公開ノート, 構造的カウンター）**: well-piloted spread。**vs v009 = 0.775**（弱pilot 0.19→強pilot 0.775＝deck⊗pilot 実証）。
  だがメタ内封じ込め: vs ex 0.40 / vs Crustle **0.00**(Safeguard が Dragapult-**ex** ダメージ無効) → **weighted field 0.474<0.50**。
  → ピボット非推奨, 監視継続。出典: `exp020_deckinnov/{load_dragapult.py, eval_dragapult.py}`。
- **メタ内位置（0624 シェア: ex39/非ex26/Crustle11/Alakazam11）**: v009 weighted field ≈ **0.66**（強み: ex0.87/Crustle0.75/Alakazam~0.6＝61%を制圧, 弱み: ミラー0.40のみ）。
  ＝三すくみの好位置。カウンター余地は薄い（唯一の構造的カウンター Dragapult は 0.47 でメタ不利）。出典: `exp011_meta_watch/results/meta_*.json`。

## J. 図表→データ出典 対応
| 図 | データ出典 |
|---|---|
| 強さ序列バー | exp002 総当たり / 各 SESSION_NOTES |
| belief vs placeholder | exp008 SESSION_NOTES（0.083 vs 0.417） |
| メタ回転タイムライン | exp011 results/meta_*.json, top_*.json |
| 三すくみ図＋prize liability | §D, §F |
| v006/v007 マッチアップ行列 | exp012 test_nonex.py / test_smart.py, analyze.py(v006_0620) |
| LB 推移 | submit/SUBMISSIONS.md, submissions.csv |
| ミラー smart-vs-generic 0.775 | exp012 test_smart.py |
| RL 3重ネガティブ | exp010 results/rl_phase{2,3}_history.json, SESSION_NOTES |
| **exp014 value較正 段階別AUC** | exp014 results/value_calib.json, value_calib_rich.json |
| **トップ戦略(charmq apex 0.70)** | exp011 results/top_charmq.json, exp014 dataset analysis |
| **規律パッチ ミラー0.55(patched vs generic)** | exp018 eval_mirror.py / eval_compare.py (n=200) |
| **3変種探索 ≤0.47** | exp015 eval_tactical.py |
| **メタ内位置 weighted 0.66 / Dragapult 0.47** | exp011 meta_*.json, exp020 eval_dragapult.py |
