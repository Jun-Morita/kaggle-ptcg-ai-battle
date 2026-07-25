
## Step 1 結果（07-21、1日分）

```
4,612 エピソード解析、チーム名のLB照合率 100%（未知0件）
教師サンプル（≥1000点 かつ 勝利）: 3,802件／日
  mixed_ex3 1604 / mixed_ex1 876 / mixed_ex2 675 / dragapult 329 / crustle 215
```

供給は十分。Alakazam 特化なら6日で 5,256試合 ≈ **31万決定**で、
外部で18位を取った Tony Li の 168,626決定を上回る。処理は 21.5GB を約3分（zipから直接）。

## Step 1 の副産物: 上位帯メタの判明（今日最大の発見かもしれない）

| アーキタイプ | 上位帯(≥1000) | koff の対戦相手(~886) | 実体 |
|---|---|---|---|
| **mixed_ex3** | **43%** | 9.5% | **Marnie's Grimmsnarl ex + Munkidori + Froslass**（悪、Spikemuth Gym） |
| mixed_ex1 | 28% | 28.6% | Alakazam |
| **mixed_ex2** | **18%** | 2.0% | **Team Rocket's Spidops**（Tarountula/Spidops/Mewtwo ex） |
| crustle_control | 8% | 8.2% | |
| dragapult | 7% | 6.8% | |
| **mixed_ex4** | **1.7%** | **20.4%** | Archaludon |

### 訂正: H12（TR Spidops）の棄却は射程を誤っていた

今朝「我々の帯域では1.9%だから優先しない」と棄却したが、**pilkwang の 12.3% は上位帯の数字**
だった。実際、上位帯では 18%。TR Spidops は Safeguard 系のキラーで、koff（Crustle Safeguard が
防御の柱）は上に行くほど狩られる構造だった。デッキ乗り換えはこの点でも結果的に正しい。

### より重い問題: プールが「今いる帯域」をモデル化している

上位帯の 43%（Grimmsnarl）+ 18%（TR Spidops）= **61% について実戦データがほぼ無い**
（koff の mixed_ex2 が 0-3 のみ）。
逆に mixed_ex4 は我々の帯域で 20.4%・v025 が 0.800 で得意だが、上位帯では 1.7%。
→ **今日見積もった +0.030 のうち mixed_ex4 由来分は上に行くほど消える。**

## 優先順位の変更

BC より先に **上位帯の相手プールを作る**。
1. デッキは既に手元（3,802件のスキャン結果から抽出可能）
2. 費用がBCより遥かに安い（数時間）
3. **BCの評価にもこのプールが要る**。今のプールでBCを評価しても、行かない帯域を測ることになる

教師データはそのまま使えるので無駄にならない。むしろ足切りを正しい相手で行えるようになる。

## Step 2 決定（07-23 午後）: 教師デッキを Alakazam → Grimmsnarl に変更

外部情報（disc728071 で2人が独立に「同じ checkpoint でもデッキでスコア激変」、disc724362 で
「#1以外のトップは探索なし＝純argmax BC がトップ帯に実在」）＋ 我々の上位帯メタ実測が同じ方向を指す。

| | Alakazam (mixed_ex1) | **Grimmsnarl (mixed_ex3)** |
|---|---|---|
| 上位帯シェア | 28% | **43%（最多）** |
| 教師サンプル/日 | 876 | **1,604（最多）** |

最も打たれ・最も教師データが多いデッキで BC を組むのが silver 帯（＝これから行く場所）に最も効く。

### build_records.py（新規）: 教師インデックス → 日次zip ストリーム → 12-tuple

exp041/replay_to_records.py は「単一チーム名＋キャッシュ済み per-sub dir」向けで、今回の
「複数教師の勝利シート＋日次zip」には使えないため新規作成。obs→action の対応は exp041 で検証済みの
next-step 則（steps[t+1] の action が steps[t] の obs への応答）をそのまま踏襲。outcome は全件 +1
（勝利シートのみ抽出済み）。

スモーク20試合: recorded 1,766 / obs_fail 0 / feat_fail 0 / nomatch 37(2%)。
相手ミックス = mixed_ex3 661・mixed_ex1 457・crustle 340・dragapult 182・mixed_ex2 126
（Grimmsnarl が上位帯の spread を倒している自然な分布）。

### 事前登録した足切り（07-23、Grimmsnarl 基準に更新）
1. 1日分（1,604試合 ≈ 14万決定）の Grimmsnarl 勝利手を教師に BC（pretrain.py, oracle-dropout 込み）
2. numpy 蒸留（export_pure.py + npnet.py、パリティ検証済みパイプライン）
3. 生の argmax ネット（探索なし）を **pub1034 stock の Grimmsnarl と mirror で n≥200**
4. 合格ライン: **勝率 ≥ 0.55**。不合格なら即撤退、17件目のネガティブとして記録

注: 足切りの相手は「行かない帯域」でなく上位帯の実デッキ（Grimmsnarl mirror）にする。
これは上で述べた「BC の評価に上位帯プールが要る」問題への直接の対処でもある。

## Step 2〜4 実行結果（07-23 夕）: 足切り PASS（16連敗後の初ポジティブ）

### ビルド → 学習 → 蒸留
- `build_records.py`: Grimmsnarl 教師 1,604試合 → **145,950 決定**、obs_fail 0 / feat_fail 0 / nomatch 1.4%。
  相手分布＝上位帯メタそのもの（ミラー37.5%・Alakazam25%・TR Spidops19%・crustle9%・drag7%）。
- `pretrain.py`（3ep, opp-drop 0.5）: **oracle-free top-1 acc 0.585**（oracle 0.584 と同等＝オラクル非依存で出荷可）。
- `npnet.py` export+parity: **argmax 500/500 一致**、`weights_pure.pkl` 51.2MB（純stdlib）。

### 足切り（事前登録）: PASS
`eval_gate.py` net(Grimmsnarl modal) vs pub1034 mirror、oracle-free、n=200:
**131-69-0、winrate 0.655、0エラー（z≈4.4）**。バー0.55を明確に超過。ミラーは両者同一デッキ＝
パイロット交絡なしの**唯一クリーンな読み**。→ net は Grimmsnarl を有能に操縦できる。

### スプレッド（穴チェック）と、その解釈の訂正
`eval_spread.py` net(Grimmsnarl) vs pub1034(各デッキ) n=100:
```
ミラー   0.740 | Alakazam 0.120(穴) | TR Spidops 0.870 | Crustle 0.840 | Dragapult 0.810  加重0.632
```
一見「Alakazam に壊滅穴」だが、**pub1034 は Alakazam 専用エージェント（exp057_pub_alakazam_＋探索）**。
Alakazam 列だけ専用パイロットの母艦、他列は素人操縦＝**スプレッドは pub1034 の交絡でラダー予測に使えない**。

### 地上真実: 実ラダー上位 Grimmsnarl の相手別勝率（≥1000 LB、日次zip 全走査）
```
ミラー 0.491(n=1192) | Alakazam 0.523(799) | TR Spidops 0.598(552) | Crustle 0.522(224) | Dragapult 0.528(218)
```
→ **実 Grimmsnarl は全マッチ 0.49〜0.60 のバランス型**。43%シェアと安定で上がるデッキ。
→ Alakazam は実際は 0.52 のほぼ五分。**net の 0.12 は matchup 限界でなく約0.40 の学習ギャップ**
  （探索付き Alakazam への守りを1日分データでは学べていない）。ミラー・他マッチは有能なので局所的な穴。

### 判定と残る選択
- **レーンは生きている**: クリーンなミラー足切りで初のポジティブ（0.655）。ヒューリスティックで
  埋められなかった操縦技量ギャップを、模倣学習が実際に埋め始めた。
- **出荷前の未解決点**: 強い Alakazam パイロットへの 0.12。実 Grimmsnarl は 0.52 なので伸びしろがある。
  候補: (a) 教師データを複数日に増やす、(b) epoch/net 拡大、(c) Alakazam 対戦の重み付け。
- 提出物ビルド（build_np_submission.py + Grimmsnarl deck.csv）＋クラッシュ安全スモークは未実施。
  初のニューラル提出＝大きな方針転換のため、実提出はユーザー判断を仰ぐ。

## 外部知見: disc717697（Abhyuday, 純RL自己対戦で silver 到達）— BC頭打ち時の次手

07-23 に本文＋コメント48件を精読。純RL（自己対戦）の別レーンだが、学習エージェントが silver に
届く独立の存在証明で、我々のBCレーンへの追い風。技術的な核心:

- **繰り返し強調される最重要レバー＝「表現(representation)」**。「observation space が判断に十分
  リッチか慎重に監査せよ」「特にどのデッキに弱いかを見よ」を2度。<2M params、単GPU ~7k SPS、~4h で
  上位公開botに勝ち、バグ修正後 silver。学習中に 250 unique cards（ラダーの95%）を「使う側・倒す側」
  両方で見せる。
- 別RLチーム Jake: ローカル9デッキ・学習6＋ルール3のミニトーナメント、一部hold-out検証。相性は公開
  corpusとほぼ一致するが **Dragapult だけ想定より弱い**。Dapp: ローカル強いのにKaggle転移せず(~800頭打ち)。

**我々への含意（バックログ化）**: 今日の **Alakazam 穴(0.12) は Jake の「Dragapultだけ弱い」/ Abhyuday の
「どのデッキに弱いか→表現を監査」と同じ症状**。今の対処（複数日データ追加）で縮まなければ、次の診断は
データ量でなく**表現**に向ける — 公式サンプルのエンコーダが Alakazam 対戦の守りに必要な特徴を捉えて
いるか。BC が頭打ちになった時の最有力の伸びしろ候補として記録。

## Step 5（07-23 夜）: 5日データで再学習 → Alakazam 穴が3倍縮小

`build_multi.py` で 5日分（07-18〜22）を record化: **762,255 決定 / 8,331 Grimmsnarl 教師試合**。
**Alakazam 対戦例 36k→223k（6倍）**。`pretrain.py`（3ep, opp-drop 0.5, tag pre_grimm5）→ parity 500/500。

top-1 acc（oracle-free）: 全体 0.585→**0.617**、**Alakazam(mixed_ex1) 0.571→0.636**（穴に効くデータ増が最も効いた）。

再測定（pub1034 相手、モデル pre_grimm5/model_ep2）:
| マッチ | 1日 | 5日 |
|---|---|---|
| ミラー足切り(n=200) | 0.655 | **0.865**(173-27) |
| Alakazam | 0.120 | **0.360** |
| TR Spidops | 0.870 | 0.970 |
| Crustle | 0.840 | 0.890 |
| Dragapult | 0.810 | 0.980 |
| 加重 | 0.632 | **0.781** |

- **穴はデータ量で縮む＝学習不足だった裏付け**（1→5日で 0.12→0.36）。Alakazam は依然最弱だが、pub1034 は
  Alakazam 専用機で、実ラダー平均の Alakazam には上位 Grimmsnarl が 0.523 なので**実戦勝率はこれより高いはず**。
- クリーンな読み＝ミラー足切り 0.865（pub1034 圧勝）。スプレッドは pub1034 の交絡ありだが全マッチ 0.36〜0.98。
- **判断**: BC はローカルで明確に機能。次は**実ラダーでの確定**（全 BC 証拠がまだローカル/交絡付き）。
  提出物ビルド＋クラッシュ安全スモーク → 実提出はユーザー判断。残る Alakazam は出荷後の改善対象
  （さらにデータ増、または表現監査レーン）。

## Step 6（07-23 深夜, v034収束待ち）: 弱点2つの切り分けと10日データ化

### 純ウォール 0.000 はデッキでなく専用スタッル操縦由来（裾リスクに格下げ）
スモークで net が exp007 ウォール（make_crustle_agent）に 0.000 だったが、**同じウォールデッキを
pub1034（素人操縦）が握ると net は 0.810**（81-19, n=100）。つまり 0.000 は**デッキ/matchup でなく
exp007 の専用スタッルパイロット由来**。exp007 wall は現メタ crustle_control と 33/60 一致の off-meta 純ウォール。
実帯域の crustle_control（8%、上位 Grimmsnarl 0.522、net は pub1034相手 0.89）には問題なし。
→ ウォールは「専用スタッルbotがラダーに居れば」の裾リスクで、キャップではない。

### 確実なスコアアップ: 教師データを10日に倍増 → v035
1→5日で全マッチ単調改善（ミラー0.655→0.865, Alakazam 0.12→0.36）した実績から、追加5日（07-13〜17）を
取得して10日コーパスで再学習。build_multi は episodes_* を全 glob。

10日コーパス: **1,083,793 決定 / 12,235 試合**。相手構成で **Alakazam(mixed_ex1) が最多 370k**（古い日ほど
Alakazam 対戦が多い）。top-1 acc 0.624（5日 0.617 / 1日 0.585）。parity 500/500。

v035 ゲート（pre_grimm10/model_ep2, pub1034相手）:
| マッチ | v034(5日) | v035(10日) |
|---|---|---|
| ミラー足切り(n=200) | 0.865 | **0.910**(182-18) |
| Alakazam | 0.360 | **0.370** |
| TR Spidops | 0.970 | 0.960 |
| Crustle | 0.890 | 0.780 |
| Dragapult | 0.980 | 0.970 |
| 加重 | 0.781 | **0.789** |

### 【重要】Alakazam でデータ・レバーが枯れた
1→5日: Alakazam 0.12→0.36（大）。**5→10日: 0.36→0.37（対戦例 223k→370k なのに動かず）**。
＝ Alakazam の残ギャップはもうデータ量では埋まらない。**次のレバーは表現**（disc717697 の
「representation is the key lever」）、または pub1034-Alakazam が探索付き専用機で純argmax では割れない事実。
ミラー・他マッチは 0.78〜0.97 で健全。

### v035 提出（sub 54931898）
ユーザーが「ゲート合格なら提出まで」を事前承認。全ゲート合格（ミラー≥0.55・新穴なし・スモーク120試合0err）。
**v033 alakazam(795.4, 非メダル圏)を退避** → eligible = {v034 5日BC 563.9, v035 10日BC} ＝両枠BC。
5日/10日の2プローブで BC のラダー有効性の信号を倍化する狙い。v034 のラダー読みは ~7-8試合でまだ不定。

## Front 2 レバー測定 = NO-GO（07-24）: MCTS は探索で悪化

「レバーを先に測る」規律に従い、AlphaZero ループ構築の前に MCTS が効くかを測定。
**自己ミラー**（net-MCTS(sc16) vs net-raw、Grimmsnarl 両サイド、pub1034 交絡なし）:
```
MCTS vs raw: 18-42 = 0.300, z=-3.10  (n=60, 227s)
```
**探索はネットの手を有意に悪化**（exp010/exp040 の「more search = worse」）。価値ヘッドが MCTS を
支えられない＝AlphaZero ループは不成立。数日の投資を4分で回避。

→ **Front 2（self-play/MCTS）は打ち切り**。BC 単体キャップ（583/prvsiyan~750 < koff~810）＋全帯データ
不在＋MCTS逆効果 で、本コンペの学習レーンは網羅的に出尽くし（24ネガ＋this）。silver は Front 1（koff
リロール）に集約。

## exp081 Track A（07-25）: koff-vs-Grimmsnarl 診断 = 構造的レース負け、パッチ不可

「今出せる提出物の改良」で唯一の未調律ターゲット＝koff の対 Grimmsnarl（ラダー 0.29、Grimmsnarl は
新台頭でkoffが一度も調律していない）を診断。`eval_diag.py`: koff(LO) vs 我々のBCネット(Grimmsnarl,
oracle-free, ミラー0.91の稽古台) n=100。

結果:
```
koff 75-25-0  koff_winrate=0.750   (BCネットは弱い稽古台=ラダー0.29を再現せず)
koff WINS  (n=75): turn~29  相手山end~0   相手プライズ残~4  (=ミル完遂で勝つ)
koff LOSES (n=25): turn~25  相手山end~8   相手プライズ残~2  (=相手が4プライズ先取、koffは山8残しでミル未完)
```
**負け方 = プライズ・レース負け**。koff(control-mill)が Grimmsnarl(aggro-ex)のプライズ時計に間に合わない。
turn25で決着（勝ち試合の29より早い）、koffは山を8まで削るが完遂前にプライズ6-2で負ける。
これは control vs aggro の古典的な時計負け＝**構造的、パッチ可能な gated-decision 漏れではない**。

さらに **有効な局所計器が無い**: 我々のBCネットは弱すぎ（koff 0.75 vs ラダー 0.29）、pub1034 は過大評価。
→ 仮にkoffをパッチしても局所A/B検証不能（pub1034ゲート失敗と同じ轍）。
**→ Track A（koff-Grimmsnarlパッチ）は棄却。学習だけでなくヒューリスティック改良レーンも出尽くし。**

## exp081 副産物: koff ≈ alakazam（安定メタで互角）— 「alakazam有利」はノイズだった

現メタ再重み付けで koff と alakazam を比較（両ビルドの実ラダー archetype 別勝率）:
- **ノイズ・スナップショット（Grimmsnarl 24%）**: koff 0.51 < alakazam 0.55 ← 一時的
- **安定平均シェア（7スナップショット, n=562）**: **koff 0.550 ≈ alakazam 0.537** ← koff微差で上
安定メタの最大2勢力は Alakazam ミラー(mixed_ex1 23%) と Archaludon(mixed_ex4 21%)=計44%。
koff は Archaludon 0.90 で稼ぐ / alakazam は Grimmsnarl 0.53・dragapult 0.62・lucario 1.00 で稼ぐ＝相補的。
**{koff, alakazam} のヘッジは正しい。alakazamは明確に上ではない。**

真の天井: **最大勢力 Alakazam(23%) を我々のどのビルドも倒せない**（koff 0.46 / alakazam-mirror 0.36 /
BC-Grimm 0.37）。ここが唯一の未探索・高レバー領域だが、ミラー調律は exp058/075 で既に NO-GO。

## exp081 Track B（07-25）: anti-Alakazam レバー測定 → dragapult が最良archetype

「レバーを先に測る」規律で、ビルド前に silver帯(both>=900)の全 archetype×archetype 勝率行列を実データ
から構築（alakazam_predator_scan.py → matchup_matrix.py、10日分、n=数千/セル）。

### Alakazam(mixed_ex1)の天敵
- mixed_ex2 が Alakazam を 0.690 で叩く（n=2985）/ dragapult 0.553 / crustle 0.474 / mirror 0.500
- だが mixed_ex2 は総合 0.509 = narrow tech（Grimmsnarl 0.40/dragapult 0.36/ex_beatdown 0.28 に折れる）
  ＝anti-Alakazam 特攻は silver vehicle にならない（罠）。

### silver帯 archetype 別 総合勝率（メタ加重, stable shares）
mixed_ex5 0.612(share0.012レア) / dragapult 0.576(0.069)←最良 / mixed_ex1 0.558(0.233) /
ex_beatdown 0.544(0.053) / mixed_ex3 0.526(0.112) / mixed_ex2 0.509(0.020) /
crustle_ctrl 0.492(0.085)←koffのarchetype負け越し / mixed_ex4 0.442(0.206) / non_ex 0.442(0.109) /
lucario_ex 0.342(0.098)

### 重大な帰結
1. koff(crustle_control)は silver帯で 0.492 = 構造的負け越し。942高ドローは下位帯分散で、post-deadline
   収束（真の実力≒2週間）では <0.5 へ回帰＝reroll は silver に信頼できない道。（ただし我々koffは
   Archaludon 0.90 >> archetype平均0.469＝平均超えのcrustleパイロット。それでも上限あり）
2. dragapult(0.576)が silver帯で最良の一般archetype。Alakazam(23%)に勝ち(0.553)、我々の全ビルド
   (0.54-0.55)を上回る唯一の現実的アップグレード。弱点は ex_beatdown 0.40(5%)のみ。
3. dragapult spread: vs Alakazam0.553/vs非ex0.727/vs mixed_ex2 0.643/vs crustle0.468/vs Grimm0.449/
   vs ex_beatdown0.400。安定勝ち越し。
→ 次: 強い dragapult パイロットの入手可否（公開採用 or 自作）。archetype平均≠強いパイロットの壁は依然。
