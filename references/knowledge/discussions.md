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
