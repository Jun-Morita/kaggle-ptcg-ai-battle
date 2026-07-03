# Discussion Knowledge

Kaggle discussion から得た知識を要約する。

## Entries

```markdown
## YYYY-MM-DD: title

- Source:
- Fetched at:
- Author:
- Competition:

### Key Ideas
- 

### Useful for This Competition
- 

### Risks / Caveats
- 

### Experiment Candidates
- 
```


## 2026-06-18: メタ情報（外部記事 automaton-media + ラダー実データ）

- 記事: https://automaton-media.com/articles/newsjp/ai-battle-challenge-20260617-450193/ （2026-06-17, Simulation）
- **ラダー上位は "anti-ex コントロール" が支配**。記事: 上位10は Ironmoth + Omanyte のみのポケモン構成＋トレーナー/エネ。
  Ironmoth 特性=相手ポケモンex のダメージ無効 → 公式サンプルの ex デッキ(Mega Lucario/Abomasnow)を hard counter。
- **裏取り（kaggle leaderboard 実データ, 06-18確認）**: top 1282.6 / 1222.9 / 1154.9 … 対し **我々 v001=915.2**。
  約370点差＝**頂点は別アーキタイプ**。記事のメタ主張と整合。
- **注意（要検証）**: "Ironmoth"/"Omanyte" は我々のカードプール(EN/JP all_card_data 1267種)に**名前一致せず**。
  記事は別表記/不正確の可能性。ただし **anti-ex メカニズムはプールに存在**:
  - Sylveon(330) Safeguard / Crustle(345): 相手ポケモンex の攻撃ダメージを全無効。Farigiraf ex(83): 相手の基本ex 無効。
- ex は全プール中 121種。非ex の attacker(HP≥100) は 469種（Safeguard 壁を貫通できる側）。
- AI の非効率: 多くが Safeguard 持ちに ex で無駄攻撃（記事指摘）。

### 競技への含意（重要）
- **デッキ選択が決定的レバー**。全-ex の Lucario は構造的にメタ負け＝915 で頭打ちの主因。
- 勝ち筋: (i) anti-ex コントロール(Sylveon/Crustle 壁＋妨害トレーナー)を自作、(ii) **非ex attacker** デッキで Safeguard 貫通。
- 我々の agent は lucario_v2 のカード個別知識に依存＝**新デッキには方策の適応が必要**（exp007 の課題）。
- メタは2ヶ月で変動する前提（締切 Sim 8/17, Strategy 9/14）。リプレイ(forum 日次export)で継続監視。

### 2026-06-18: 自分のリプレイによるメタ実証（v001, 11ゲーム）
- リプレイ DL: `kaggle competitions episodes <submission_id>` → `kaggle competitions replay <episode_id>`（raw: references/raw/replays/, gitignore）。
- v001(Mega Lucario) 11戦 = **7勝4敗**。**敗北4件は全て純 Crustle コントロール**（Dwebble×4 Crustle×4, ex 0, 残りトレーナー/エネ）。
- 勝ち: Lucario ミラー×4 / Alakazam系(Abra-Kadabra-Alakazam)×2 / Crustle+Chi-Yu型×1。
- **確証: 記事の「anti-ex control」= 本プールでは Crustle(345)+Dwebble。我々の全-ex Lucario は Crustle に 100% 負ける**
  （ex 攻撃が Safeguard で無効）。Alakazam やミラーには勝てる。
- リプレイ JSON 構造: `steps[step][agent]` に action/observation/status/reward。デッキ=len60 の action。
  config: actTimeout(episodeにより 0 or 1), runTimeout=1200。v002(PIMC)は actTimeout=0 のエピソードで178手10分を**完走（タイムアウト無し）**
  → v002 の LB 850<915 はタイムアウトでなく「メタ負け＋ミラー優位なし」が真因。

### exp007 への確定要件
- **目標: Crustle anti-ex control に勝てるデッキ＋方策**。打ち手:
  (i) 非ex attacker で Crustle を殴る（Safeguard は ex のみ無効。現Lucario の Hariyama/Solrock/Lunatone は非ex だが方策が ex を優先して無効攻撃している）。
  (ii) 専用アンチコントロール（強い非ex attacker＋デッキアウト/妨害対策）。
  (iii) 自分も Crustle control を組む（メタ同型）。
- 評価プールに **Crustle control を追加**（現プールは ex 同士でメタ未反映）。Crustle の勝ち筋（deckout? 非ex/Chi-Yu 攻撃?）を要分析。

### 2026-06-18: トップ戦略の分析＝実ポケカ「Safeguard 壁コントロール」
- Crustle 戦リプレイ精読(16ターン96手): 我々 Mega Lucario が**39回攻撃→全0ダメージ**、サイド0枚。
  Crustle が120×複数回＋回復で消耗戦に持ち込み**サイド3枚取って勝利**。典型的な attrition control。
- **実ポケカ同型**: 「相手の ex(/GX) のダメージを無効にする特性」を軸にした壁コントロール（現実の Mimikyu/Sylveon Safeguard 系）。
  本プールでは Crustle(345) "Mysterious Rock Inn"。回復(Jumbo Ice Cream/Cook/Waitress)＋ドロー(Lillie)で完封。
- **メタ三すくみ（実測 n=16）**:
  - Crustle control は ex デッキを食う: vs Lucario 0.75 / vs Dragapult 1.00。
  - 非ex attacker(v003 anti-crustle) は Crustle を食う: v003 0.62 vs mimic。
  - → ex attacker → (負ける) Crustle 壁 → (負ける) 非ex attacker → (ex に強い…) の循環。
- **2枚看板戦略**: A=Crustle control 模倣（ex 環境を制圧, v004）, B=anti-Crustle カウンター（v003, 提出済）。
  ラダー構成次第で最適が変わる→両方提出し LB で比較。Strategy レポートはこの三すくみ分析が独自性の核。

### 2026-06-18(夕): 高レート帯メタの進化（v003 ~1100 の対戦20件解析）
- リーダーボード TOP: Praxel 1388 / Kadoraba 1267 / 上位帯 1180-1270。我々 v003=1123/1099（最新2枠確保済）。
- v003 戦績(20件): **Crustle control 5W-4L（唯一の苦手, 敗北は全てこれ）/ Mega Lucario 6-0 / Alakazam 3-0 / 多ex 1-0 / 炎非ex 1-0**。
- **Crustle が非ex 炎アタッカーを搭載して進化**: Ethan's Cyndaquil(352,Ember30), Chi-Yu(31/719,60), Centiskorch(934,130)。
  → 「ex無効の壁＋自前の非ex打点」二刀流。pure wall が anti-ex(v003)に食われる弱点を、非exアタッカーで補強。
- v003 が Crustle に互角どまりの主因: Crustle+Hero's Cape=250HP は Hariyama 210 で一撃不可、回復(Jumbo80/Cook70)、相手も殴り返す。
### カウンター/模倣の余地
- カウンター強化: Boss's Orders で未育成 Crustle/Dwebble を引きずり出して先に処理 / tool 除去(Hero's Cape剥がし) / 2パン用の継戦力＋自己回復 / デッキアウト促進。**pure 非ex デッキ**（ex を積まない＝腐り札ゼロ）も候補。
- 模倣強化: 我々の v005 制御(835収束中)は pure wall。TOP同様 **Crustle＋炎非exアタッカー**を積み、壁と打点を両用する制御方策にすれば上位射程。事故率(マリガン/序盤展開)とミラーが課題。
- 大方針: メタは anti-ex 支配＝**全-ex デッキは死に筋**。勝ち筋は非ex 中心に寄せる。

## 2026-06-24: 公式 disc 708586 — シミュレータ vs 公式ルールの差分（運営公式）

- Source: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/708586 （運営 shimishige / Addison Howard / 上位 gagacrow 102位ら）
- raw: `references/raw/discussions/708586_sim_vs_official_rules.md`（gitignore）。INDEX の「要取得」を回収。
- **大原則: シミュレータの挙動が正（公式ルールと違っても sim が canonical）**。

### 我々に効く実装ノウハウ（actionable）
- ★**セットアップのベンチは任意**: `select.context == SETUP_BENCH_POKEMON` かつ `minCount==0` のとき
  **`[]`（または部分集合）を返してよい**。「end turn」option が無いのは仕様＝全 basic を並べる強制ではない。
  → **我々の pilot は SETUP_BENCH を未スコア化（`_score_card_choice` に分岐なし→全 option score 0→`ranked[:maxCount]`＝
  毎回 basic を全並べ）。v009 規律パッチは MAIN の play のみで、セットアップ並べを覆っていない**＝サイド責任の観点で要検証レバー。
- **ABILITY(opt type 10) = 明示的に選ぶ起動特性 / SKILL(15) = 受動・常時効果**。Clefairy 系の常在効果は自動発動＝毎ターン option で再起動不要。
- **ベンチに下げると効果が「クリーン」化**: Mega Brave 等「次ターン攻撃不可」制限は、退却→ベンチ→再 active で**リセットして再使用可**（運営確認済）。攻撃制限持ちの戦術レバー。
- Mega Lopunny "Gale Thrust" のボーナスは「ベンチ→active へ移動」が条件。**active で進化しただけでは不発**（"this Pokémon"=進化後を指す, 60 dmg が正）。
- Telepathic Energy: どのタイプに付けても任意ポケモンをサーチ可（2枚とも手札へ）。
- 一部攻撃は宣言だけして効果不発で終了するケースを、sim では**最初から選択不可**にする（空ベンチで「ベンチに出す」攻撃など）。結果は同等。
- Mega Zygarde ex "Nullifying Zero" は対象順を選べず左→右で自動コイン。同時 KO のサイド取得順も sim 独自（両者全取り=引き分け）。

### Experiment Candidates
- **setup-bench 規律**: SETUP_BENCH_POKEMON で benching を制限（開けておく/必須ライン以外を並べない）→ サイド責任↓ を n≥200 ペア比較で実測。
  thesis（[[meta-and-leaderboard]] の prize-liability 規律）と整合だが、序盤展開速度↓のトレードオフあり＝**勝ち確定でなく要測定**。
- 攻撃制限リセット（退却 reset）を pilot が活用できるか（現状 Mega Brave 周りのみ）。

## 2026-06-25: disc 711737 — engine ソース/リバースエンジニアリングの裁定要求（運営未裁定）

- Source: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/711737 （c-number 192位 → 運営 shige）
- raw: `references/raw/discussions/Request for an explicit ruling on game engine source...md`（gitignore）。
- 要求: engine ソース公開の有無／`.so`/`.dll` のリバースエンジニアリング・再実装の可否／チーム横断の公開共同エンジンの可否を**明示裁定**してほしい。

### Key Ideas / 事実
- **engine は binary（`.so`）＋wrapper のみ。ソース未公開。** ローカル検査可能エンジンは RL・木探索の高速化に不可欠。
- **運営回答（shige, 3日前）=「検討中、近く明示的に回答」。⇒ 現時点で可否は未裁定（グレー）。**
- **提出側エンジンは公式固定**: tarousan_imo が ctypes 13関数を LLM 再実装→ローカル可だが Kaggle 提出で **500 エラー**＝自作エンジンは**ローカル学習/探索専用**。
- greySnow: Claude Code 2日でカードテキスト＋公式エンジンを oracle にエンジン自作「実装・反復はできるが**真エンジンとの差分は残る**」。別案=binary 内部 cracking で **pickling 段（時間の大半）をバイパス→木探索 *10 高速化**（本人未検証）。

### Useful for This Competition（我々＝ルールベース pilot＋公式エンジン）
- **直接の打撃小**: 我々は自作エンジン不要（RL/探索は honest negative [[rl-status]]）。エンジン非公開は **RL/探索勢にこそ効くハンデ**。
- **追い風（レポート材料）**: 提出は公式エンジン固定＝**純ヒューリスティック＋公式エンジンは完全再現可能**＝Strategy 評価軸「安定性/再現性/頑健性」でプラス。リバースエンジン依存解は再現性リスク。

### Risks / Caveats
- リバースエンジニアリングは**未裁定**＝IP/失格リスク。**今は投資しない／公式裁定を待つ**。
- 中長期脅威: 上位 RL 勢が高速ローカルエンジンで、我々が特定した壁＝**engine throughput / マルチターン sequencing**（[[meta-and-leaderboard]] 2026-06-25 take-when-legal）を攻略し天井を上抜く可能性。ただし greySnow が「差分残る」と認める＝過大評価禁物。

### Experiment Candidates
- なし（コード変更不要）。**公式裁定をウォッチ**し、「再実装/共同エンジン許可」が出たらメタ天井上昇を前提に方針再評価。

## 2026-06-25: disc 711741 — 1 agent で複数デッキは可か（運営未裁定）

- Source: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/711741
- 問い: cabt は deck.csv を直接読まず**エージェントが毎ゲーム recipe を渡す**＝機構上 agent は毎試合デッキを変えられる。1提出で multi-deck は許される? OP 予想=「No（per-game 戦略より meta-game に偏る）」。**運営未裁定。**

### Key Ideas（自分のラダーリプレイで確認済）
- **機構上 multi-deck は可能**: 我々のコード `if obs.select is None: return list(deck)`＝step1 で60枚リストを返す＝別デッキを返せる。
- **★決定的: デッキ選択は完全ブラインド** — 60枚を返す瞬間の obs は両者 `active=[]/bench=[]/deckCount=60/hand=0`＝**盤面空・相手情報ゼロ**。⇒ **相手を見てからの counter-pick は不可**。可能なのは試合をまたぐ**ブラインド混合戦略**のみ。

### Useful for This Competition
- 概念的には我々の三すくみ問題（非ex は mid-field 頂点だが gold 帯でカウンターされる）への混合戦略ヘッジになりうる。**だが実益薄**:
  (1) 未裁定リスク, (2) **deck⊗pilot 結合**＝各デッキに有能 pilot 必須だが我々は Mega/Alakazam/Dragapult を競技ピロット不能（exp022）→混合は弱デッキを抱えレート希釈, (3) **eligible=最新2提出が既に準拠した2デッキ・ポートフォリオ**＝agent内 multi-deck 不要。

### Risks / Caveats
- 未裁定＝**multi-deck 提出は作らない**。許可されても我々は2枚目を操縦できず優先度上がらず。律速は piloting（[[meta-and-leaderboard]] take-when-legal）でデッキ切替でない。

### Experiment Candidates
- なし。公式裁定ウォッチ。レポートに「ブラインド選択機構＋準拠した最新2枠ヘッジを採用、未裁定 multi-deck は採らない」を1段落。

## disc 712621 — LB スコアリングの非一貫性（djschmit, 2026-06-23頃, 上位勢多数同調）取得 2026-07-03
- **事実**: 同一エージェント2回提出で 940 vs 790（150差）/ 1104 vs 687（400差超, festival lead）。
  Zhenyu Zhang「収束後1日経っても 1100+ vs 800台」。LagrangianLocomotive「7位→1100位」。
- **構造**: 初期5-10試合が支配的（μ600直後の高ボラ）→ 収束後は ±5pt/試合 → 相手選択レート帯が狭く lock-in。
  Shun_PI(#12) の4問題整理: 試合数不足/初期ボラ過大/converged分散大/マッチング帯狭い。
- **帰結**: 上位は提出を控える（ShumpeiNomura #4 も明言）→ メタ停滞。最適戦略が「連投 high-roll 釣り」化。
  6/30 環境更新（48試合/日＋random 10%）は部分対応。
- **我々への適用**:
  1. **±150pt はノイズ扱い**（自データ: v006 再提出 1086→662→971 が同現象）。
     過去の「v008/v009 ラダー退行＝ローカル過学習」結論も一部は運の可能性（レポートで交絡として明示）。
  2. v013/v014 の判定は「+150級の動き or 複数回提出での再現」を要求。
  3. **最終候補は同一2枠重複提出**（djschmit 方式）＝測定として最良 & best-of-2 の EV 最大化と一致。
  4. 最終週（〆8/17前）はベスト構成の連投を計画（全体で high-roll 釣りが起きスコアインフレ想定）。

## disc 711737 追記（2026-07-03 再分析）— ソース公開(717141)で決着した後の視点
- 経緯: c-number(20位) のルーリング要求 → host「検討中」→ **9日後 7/1 にソース公開で正式決着**（最も公平な選択肢）。
- スレッド内の実態: greySnow「Claude 2日でエンジン再実装→完全一致は困難」/ tarousan_imo「LLM で ctypes 互換再実装済
  （ローカル可・**提出は 500 エラー＝本番は公式エンジン固定**）」→ 公開前から複製投資が始まっていた。
- 公開後の環境変化: リバエン競争→**高速化競争**へ。tree/RL 勢は C++ 直結（pickle バイパス ~10x 主張）で
  残り6週の探索/学習を加速してくる前提でメタを読む。
- 我々への含意: (1) 我々の探索ボトルネックは速度でなく belief/判断の質（sub-ms/step, 予算1%未満）＝C++化の
  限界効用小・優先度中（ローカル評価スループット改善用途のみ）。(2) 本番自作エンジン不可＝「軽い探索を本番で
  直接使う」我々の路線は無風。(3) レポート: 「観測→機構推定→ソースで検証」(revenge window) は
  皆がエンジン理解に苦闘した文脈での独自性の証拠。

### 訂正（2026-07-03, disc 712621 エントリの「最終週連投 high-roll 釣り」戦略について）
overview 再確認により**釣り戦略の価値を下方修正**。決定的仕様: **「締切(8/17)後 約2週間継続対戦して LB 確定」**
＝最終 eligible 2体は ~670試合(48/日×14日)を追加消化してから確定 → 初期分散はほぼ洗い流され
**最終スコア ≈ 8月末メタに対する真の実力**。加えて (a) 凍結された過去高値（v006 1086等）は最終評価対象外、
(b) アクティブな高値は磨滅する（自データ: v001 915→841, v003 1123→999; top も 1350→1230 圧縮）。
∴ 正しい戦略 = 開発継続で真の実力向上＋最終メタ読みデッキを締切数日前に2枠。釣りは残留ノイズ分(±30-50?)の
微益のみで、開発機会費用に見合わない。disc 712621 の分散問題は「開発中の判定ノイズ」としてのみ重要
（±150 ノイズ扱い・重複提出 A/B は引き続き有効）。
