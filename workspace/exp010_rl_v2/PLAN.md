# exp010_rl_v2 — RL 再挑戦の設計（exp004 の失敗を踏まえて）

## なぜ再挑戦か / exp004 との違い
- exp004(cold-start AlphaZero)= プール 0.03 で失敗。原因: ①知識ゼロからの自己対戦は立ち上がり遅い
  ②placeholder determinization で探索が「偽の相手」に最適化＝有害。
- 今回はこれまでの知見と**複数の使える戦略**を統合する:
  1. **複数教師の BC で warm-start**（exp006 単一教師 0.389 を、多教師＋多相手で底上げ）。
  2. **belief 接地 determinization で MCTS**（exp008: 相手を実メタデッキ分布からサンプリング → 探索が有益化）。
  3. **メタ相手プールで self-play / RL 微調整**（特に Crustle control に勝てるよう）。

## 資産（教師・相手・部品）
- 教師方策: lucario_v2, v003 anti-Crustle(最良), dragapult, iono, abomasnow, Crustle control。
- 相手プール（評価＆self-play）: 同上。**Crustle control が現メタの本丸**（v003 でも 5-4）。
- 部品: exp006 の BC モデル/特徴量(Transformer value/policy, sparse EmbeddingBag), exp008 の belief determinize,
  exp004 の MCTS(PUCT)。GPU: RTX3060 12GB / torch cu124。

## 段階設計
- **Phase 1 — 多相手 BC（warm-start）**: 教師 = v003 anti-Crustle(Lucario デッキ, 我々の最良)。
  相手 = {Crustle control, lucario_v2, dragapult, iono} + ミラー。各決定の (obs→教師選択) を記録し
  policy(CE)+value(Huber) を学習。**探索なし greedy** で プール＋Crustle 評価。目標: exp006(0.389)超え、
  できれば v003 に迫る fast net。
- **Phase 2 — belief-MCTS RL 微調整**: Phase1 net を初期値に、belief 接地 MCTS(相手=メタデッキ分布)で
  self-play → TD 学習。相手プールに Crustle を含め、対 Crustle 勝率を主指標に。
- **Phase 3 — 評価・提出判断**: プール平均・対 Crustle・推論コスト(10分/試合 = actTimeout 留意)を確認。
  v003(LB1123) を超えるなら提出。超えずとも Strategy レポートの「学習系で○○」の独自性に使う。

## リスク / 留意
- BC は誤差累積で教師未達（exp006 教訓）。多相手データで分布シフトを緩和、最終は RL で補正。
- 推論コスト: 提出は actTimeout(~1s?)/runTimeout(1200s) 内に。探索付きは要速度管理（exp008 PIMC は重すぎた）。
  → BC net 単体は高速(0.1s)。MCTS を載せるなら軽量に。
- determinization は belief(実デッキ) 必須（placeholder は有害）。相手アーキタイプ推定 or メタ分布固定。
- 単一 net は1デッキで推論 → まず Lucario デッキ(v003)向けに学習。Crustle 制御版は別途。

## 評価基準
- ローカル: 固定プール平均勝率＋対 Crustle control 勝率。バー = v003(対Crustle ~0.55, プール圧勝)。
- LB: 提出して v003(1123) と比較。
