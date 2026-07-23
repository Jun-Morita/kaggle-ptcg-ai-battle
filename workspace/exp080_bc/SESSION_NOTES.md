
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
