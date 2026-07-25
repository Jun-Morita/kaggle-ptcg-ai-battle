# exp082 — dragapult 採用（skarin/Phantom Dive）: silver帯 最良archetypeへの乗り換え候補

## 仮説と出典
exp081 の silver帯 全archetype勝率行列（`../exp080_bc/matchup_matrix.py`, 10日, n=数千/セル）で
**dragapult が silver帯で最良の一般 archetype（総合 0.576、vs Alakazam 0.553）** と判明。
公式 dragapult サンプル（kiyotah）はラダー 499.6 で archetype 潜在を全く引き出せていないが、
コミュニティ版 **skarin/phantom-dive-or-go-home-a-dragapult-ex-deck**（公開, OSI, 帰属）は
**SK Arin #735 = 827.5**（我々の koff 766 / alakazam 789 より上）＝強いパイロットの安い採用パス。

## 採用エージェント
- 出典: Kaggle notebook `skarin/phantom-dive-or-go-home-a-dragapult-ex-deck`（要 submission message 帰属）
- デッキ: Dragapult ex ×3 + Dreepy/Drakloak ライン + Budew（item lock）+ Crushing Hammer×4（エネ破壊）
  + Boss's Orders×3（gust）+ Unfair Stamp（ACE SPEC）+ Latias/Fezandipiti/Meowth ex tech
- 方策: スコアリング・ヒューリスティック（ダメカン配置最適化が肝、31KB, cg.api使用）
- 安全スキャン: subprocess は tar梱包cellのみ / requests/socket/eval/exec/urllib 無し ＝ clean
- 注意: 作者の自己申告マッチ表は我々の行列と食い違う（作者「vs壁81%」vs 実測 vs crustle 0.468）
  → 作者主張は不採用、ハーネス実測で判断

## 独立評価（我々のハーネス, exp082/eval_drag.py, seat交替, n=100, 0クラッシュ）
| dragapult vs | 勝率 | メモ |
|---|---|---|
| **koff（我々の現ビルド, LO）** | **0.720** (72-28) | koffのラダー対dragapult 0.20 と整合＝現ビルドを圧倒 |
| **pub-alakazam（実Alakazamパイロット）** | **0.570** (57-43) | anti-Alakazam 達成、行列0.553と一致 |

## 提出ビルド（クラッシュsafe）
`scripts/build_submission.py --deck dragapult_deck.json --policy build_drag/main.py --out build_sub`
- tar構造OK（top-level main.py+deck.csv+cg/）、`def agent`→`_base_agent` にリネームし
  クラッシュsafe wrapper（_valid/_legal_fallback）自動付与
- スモーク 90試合 0エラー（vs lucario_v2 0.533 / vs Crustle 0.000 / vs dragapult 0.633）
- **vs Crustle 0.000 は既知アーティファクト**（exp007 の専用ストール操縦。BC-Grimmでも同様、pub1034操縦だと0.81）
  ＝実際の弱点ではない（行列 vs crustle 0.468、実 koff戦 0.72）
- タイムアウト: dragapult自身の手番は高速（vs koff 0.07s/試合）＝懸念なし

## 状態: 提出可能（build_sub/submission.tar.gz, gitignore済み）
- 提出はユーザー承認制。eligible={koff 766, alakazam 789} の **koff を置換**推奨
  （dragapultがkoffを0.72で食い、archetypeも koff crustle 0.492 < dragapult 0.576。
   alakazam 0.558 は Archaludon等で dragapult を補完＝ヘッジ維持）
- silver cut 916 に対し 827.5 は+40〜60の増分＝即silverではないが、0.576archetypeは
  koffの0.492より高均衡＝reroll vehicleとしても格上

## exp082 パイロット改良（07-25）: プライズ調整の矛盾を修正 = V3（確定改善）

skarin ロジックの通読で5点の候補を特定（詳細は下記）。テスト可能で高価値な①に集中。
③弱点は API で type/weakness が綺麗に取れず、かつ Alakazam の Abra線は全て≤140HP で 200 既KO
＝恩恵小で deprioritize。④免疫リストは koff の Crustle(345)・alakazam の Abra線を正しくカバー済み。

### ① プライズ調整の矛盾（main_option_proc 268-274行）
元コード: 勝ちに近い(remain_prize<=4)時に2プライズKOを **-1200 で罰**、1プライズ -300、0プライズ **+1200 で報酬**
＝「ばら撒いて多面KO準備」思想だが、**プライズを取る手を罰し取らない手を報酬**する逆説。

### A/B スイープ（eval_drag.py, seat交替, n=200、DRAG_DIR で変異体切替）
| variant | vs koff | vs pub-alakazam |
|---|---|---|
| baseline (skarin as-is) | 0.675 | 0.505 |
| V2 罰除去（2プライズ罰のみ削除, spread報酬維持） | 0.735 | 0.570 |
| **V3 中庸greed（prize>=2:+1500 / ==1:+500 / spread報酬削除）** | **0.735 / 0.720**(2run) | **0.615 / 0.610**(2run) |
| V4 強greed（+4000/+1500） | 0.655↓ | 0.645 |

- **V3 が sweet spot**。pooled n=400: koff **0.735**（baseline+0.060）/ alakazam **0.6125**（baseline **+0.1075, z≈3**）。
- 単調 baseline<V2<V3 ＋ V4 オーバーシュート（強greedは koff の setup を犠牲）＝ノイズでなく実最適。
- 原理的修正（矛盾除去）で control(koff)・combo(alakazam)の異archetype両方で改善＝過学習リスク低。
- V3 提出ビルド: build_v3_sub/submission.tar.gz、クラッシュ安全wrapper付与、スモーク90試合0err。

### 特定した他の候補（未実施、将来レバー）
- ② ATTACK スコア = `o.attackId`（838行）＝攻撃選択が任意ID順。実際は「setup全部→attack」の
  創発フローで機能するが、複数攻撃の使い分け不可・lethal優先せず。低インパクトと判断し保留。
- ③ 弱点未モデル化（damage=200固定）＝上記理由でdeprioritize。
- ④ 免疫カードのハードコード＝現テスト相手はカバー済み。他メタ（Grimmsnarl/Archaludon）は
  強パイロット不在で検証不能。
- ⑤ Phantom Dive の「詰め」配置＝①の改善で部分的に前進。

### 出荷判断
V3 は skarin baseline に対し両マッチ確定改善＝**現行 v038（skarin as-is）の上位互換**。
提出するなら v038 ドロー1枚を退出させて {v038, v038-V3} または {v038-V3 ×2}。ユーザー承認待ち。
