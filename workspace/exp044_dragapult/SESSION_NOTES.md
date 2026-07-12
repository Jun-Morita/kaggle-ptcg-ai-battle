# exp044 — dragapult床(0.17)の攻略: 実リプレイの行動差分→機構パッチ

## 仮説
RL(exp041系)が13件目のネガティブで頭打ちのため、ユーザー方針でヒューリスティック改良
（B案: マッチアップ床の名指し攻略）に転換。dragapultは我々の最弱マッチ
（v014ローカル0.170 / 実ラダー11W-38L=0.22）だが、**同型デッキのYushin旧提出は
15W-16L=0.48**——同じデッキで3倍勝つ打ち方が実在する。彼の実リプレイから機構を抽出し、
env ゲート付きパッチとして v014 チェーンに注入する。

## 前提: 分析ツールの信頼性
`policy_diff2.py` / `analyze_adaptation.py` / exp043 `extract_selects.py` は全て
**same-stepペアリングバグ**（`steps[t].action`は`steps[t-1]`のobsへの応答）を踏んでいる。
本実験の分析器（`analyze_drag.py`等）は検証済みのnext-stepペアリングで新規作成。

## 行動差分の発見（analyze_drag.py / early_actions.py / gust_targets.py / attackers.py）

Yushin(31試合) vs 我々のラダー(49試合)、W/L分割:

| シグナル | Yushin W | Yushin L | 我々W | 我々L |
|---|---|---|---|---|
| 初攻撃ターン | **2.7** | 4.4 | 3.0 | 3.5 |
| ベンチ数(t5-10) | **4.33** | 3.64 | 3.84 | 3.38 |
| 攻撃/試合 | 6.1 | 4.9 | 5.5 | **3.9** |
| サイド残@t10(自分) | 3.13 | 3.44 | 3.27 | **5.03** |

- **勝ち筋=進化ライン狩り**: Yushin Wの攻撃先はDreepy(70HP)13回。我々Lは
  Budew(30HP壁)37回・Dragapult ex(320HP)20回に流れる。
- **Bossの引き先**: Yushinはほぼ Dreepy/Drakloak（KO可能な1サイド）のみ。我々Lは
  KOできないFezandipiti ex(210)×4・Dragapult ex(320)×4に浪費。
- **我々Lの死のスパイラル**: t>6のPhantump素殴り(10ダメ)×40が**全て負け試合**
  （Trevenant死亡→未育成の後続を昇格→10ダメ削り→全滅）。
- ベンチ規律は逆効果の方向（広いベンチ=後続供給、exp042の教訓と整合）。
- 我々Wの特徴フェッチ: Boss 0.91(L 0.47) / **Mist 0.55(L 0.24)** / Trevenant 1.36(L 0.82)。

## パッチv1: DRAG_SNIPE（進化ライン狩りボーナス）→ **フラット、無効**

現行採点はBudew active KO(1830) > Drakloakガスト(1720) > Dreepyガスト(1570)で
壁殴りが常勝。`_rev_plan_attack`にKO可能なDreepy(119)/Drakloak(120)への+400を追加
（envゲート`DRAG_SNIPE`、OFF時はバイト同一を確認、カードID自己ゲート）。

- n=200 ONLY=dragapult: **wr=0.165** (基準0.170、変化なし)。DRAG_SNIPE=20000でも0.180——
  **条件がほぼ発火しない**。
- 診断(board_probe/target_probe): 狙える対象はベンチに81%のターンで存在するが、
  (a) KO条件(damage≥70)は Postwick+盤上Snorlax+CB+リベンジ窓の組み立てが要る、
  (b) can_gust(Bossが手札)が稀、の二重制約で「KO可能なライン狙撃」機会自体が少ない。
  攻撃の主流(400/720)は着地済みDragapult ex本体への削り。
- **結論: 採点定数1個では狙撃は再現できない。** Yushinの狙撃は複数ターンの
  組み立て(Postwickフェッチ→Snorlaxベンチ→CB→窓のタイミング)と一体
  （exp022「逐次的な知恵は静的スコアで表現できない」と同族）。フラグはデフォルト0で残置。

## パッチv2: DRAG_MIST（Mist→ベンチ後続、Phantom Diveの盾）→ n=600で有意差なし

**機構をエンジンソースで確証**（references/raw/ptcg_engine/CardImpl.h）:
- Phantom Diveのベンチ6ダメカンは`.postEffect(DamageCounterAny, Enemy).targetBench()`
  =**ワザの効果**
- Mist Energyは`.effectEnergyContinual(NoEffectEnemyAttack)`=装着ポケモンへの
  ワザの効果を無効
- → **ベンチのMist装着ポケモンはPhantom Diveのばら撒きを完全に無視**（毎ターン最大60点分）

現行`_score_attach`は**エネルギーカードの種類を完全無視**（ターゲットスコアのみ）で、
Mist(デッキに4枚)がベンチの狙われる後続に意図的に貼られることはない。パッチ:
相手盤面にDreepyライン(119/120/121)がいる時、Mist(11)→「Mist未装着のベンチ
Phantump/Trevenant」のATTACHに+400（`plan.needs_energy`時は転用しないガード付き）。

- n=200 ONLY=dragapult: wr=0.205 (41-158-1) vs 基準0.170。+0.035、方向陽性に見えた。
- **本日の教訓（pre3bのn=200上振れ→n=600で消失）に従いn=400を追加**: wr=0.175 (70-330)。
- **合算n=600: winrate=0.185 (111-488-1)、baseline=0.170に対しz=0.98——統計的に
  有意ではない**。n=200時点の0.205は上振れで、n=600では基準からわずかにプラス寄り
  (0.185)に収束するがコインフリップ圏内。

**判定: DRAG_MISTは出荷判断に足る証拠なし。** 方向性自体はまだ僅かにプラスなので
「明確な負」とまでは言えないが、「効いている」と主張できる水準でもない。
Mist装着自体はデッキ内で4枚しかなく発火頻度が低い可能性、または機構自体は正しくとも
dragapult側の他の脅威（Dragapult ex本体の削り合い、Budew壁での時間稼ぎ）が支配的で
影響が薄められている可能性がある。

## 現状の結論と次の一手
DRAG_SNIPE(無効・確定)・DRAG_MIST(有意差なし)の2機構とも、単発の採点定数追加では
dragapult床(0.17)を動かせなかった。**次の一手（未着手）**:
(a) DRAG_MISTのnをさらに積む(n=1000超)かどうか——ただしz=0.98からz=2に届くには
  相当な追加n(数千)が必要になる可能性が高く費用対効果が疑わしい。
(b) 複数機構の複合（DRAG_MIST + Postwick/Snorlax優先の組み合わせで発火条件を
  底上げ）——ただし部品の逐次的な組み立てはexp022の教訓（静的スコアでは表現困難）
  と衝突するリスクあり。
(c) この矛先を畳み、B案の他の候補（archaludon床、または元のD案=メタ的デッキ
  乗り換え）に切り替える。

## 判定ゲート（確立済み運用）
1. dragapult限定 n≥600 で基準0.170を明確に超える（+0.05以上目安）
2. 全5マッチ n=200 field評価で他マッチ無リグレッション
3. paired vs v014（別ビルド）——ただし本パッチは非ミラー限定の自己ゲート型なので、
   ミラーpairedでは差が出ない設計（ゲート3はビルドdiffの確認が主）
