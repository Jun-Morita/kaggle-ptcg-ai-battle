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
