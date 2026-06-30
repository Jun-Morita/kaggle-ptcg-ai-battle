# exp026 — Neutralization Zone (anti-ex ACE SPEC) on our non-ex deck → 誠実なネガティブ

## 動機（公開ノート 4本分析より）
Archeops 退化デッキ（archeops-draw / japanese-archeops-devolve, ともに honest negative）が
**Neutralization Zone(1247)** を採用。Stadium/ACE SPEC: 「ルールを持たないポケモンが相手 ex/V の
ワザダメージを受けない（両者）」。**我々は全 non-ex →自盤面が ex 攻撃に免疫**（Archaludon ex 220 /
Dragapult ex / Mega Lucario ex を0に）になりうる。1枚差し替え（現 ACE SPEC = Legacy Energy(12)）で軽い。

## 実装
charmq deck の Legacy Energy(12) → Neutralization Zone(1247)。policy 不変(v011 revenge)。
NZ は Stadium ＝場に出れば engine が自動適用（default 10000 で play される）。

## 測定（n=100, SE≈0.05, vs league）
| matchup | baseline charmq | +NZ | Δ |
|---|---|---|---|
| archaludon | 0.120 | 0.160 | +0.04 |
| ex_lucario | 0.690 | 0.730 | +0.04 |
| dragapult | 0.120 | 0.180 | +0.06 |
| mirror | 0.490 | 0.450 | −0.04 |
| **crustle** | 0.790 | **0.590** | **−0.20** |

## 結論: 不採用（net 中立〜微負）
- **小さな ex ゲインのみ（どれも反転せず）**: archaludon 0.16 / dragapult 0.18 止まり。理由＝Archaludon の **Duraludon(非ex Raging Hammer)** と Dragapult の Drakloak 線が **NZ を貫通**（Crustle Safeguard と同じ穴）。
- **★Stadium 競合**: NZ は Stadium ＝1枚制。**自分の Postwick(+30 打点) を上書き**＝offense 低下＋NZ uptime 低。
- **crustle −0.20**: NZ は非ex 相手に dead card ＋ Postwick(壁突破に必要) を食う ＋ Legacy Energy 喪失。
- field 重み: crustle(−0.20)・mirror(−0.04) の損が ex 系の小ゲインを相殺 ＝ **net ≈ 中立〜微負**。
- **measure-before-believing**: 「全 non-ex に anti-ex ACE SPEC が刺さる」は魅力的だが、Postwick 競合＋非ex貫通で我々のデッキには効かない。**HOLD v011/charmq**。

## 4ノート総括（採用ゼロ・intel 多）
- **ptcg-mega-lucario-ex-v62**: 我々の方法論を独立に裏付け（gated tech / moderate値 / 進化前を先に潰す）。exp023/025 と一致。
- **multiply-agent-best-940-lb**: 実 Search API(beam+MCTS) でも 940 < 我々 v006 1086 ＝探索≤ヒューリスティック再確認。
- **archeops ×2**: honest negative（化石2進化が遅い＝pilotability 律速 / CV-LB 乖離 / 過ドローでデッキ切れ）。我々の Tinkaton/TR 結論と一致。
- **Neutralization Zone**: 本実験で測定→不採用。

## 資産
- `charmq_nz_deck.json`（NZ 差し替えデッキ）/ `eval_nz.py`（DECK=charmq|nz でリーグ比較）。Archaludon opponent は exp025 を再利用。
