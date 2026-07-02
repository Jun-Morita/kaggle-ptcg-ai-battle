# exp030 — 公開 Great Tusk LO（1083.6）の脅威測定 → 非脅威で確定

## 仮説
公開 LO ノートブック（`references/knowledge/lo_mill_notebook_0702.md`, スコア 1083.6）は
我々のドロー特化非exデッキの未測定の穴かもしれない。

## 結果（eval_lo.py）
- v012（v_trev＋revenge） vs GreatTusk-LO（本人の main.py＋deck.csv そのまま, ユーザー承認済 2026-07-02）:
  **n=20: 0.90 → n=200: 0.820 (164-36-0), err=0**

## 機構（なぜ勝てるか）
- LO の防御パッケージ = Crustle **Safeguard** ＋ **Neutralization Zone**。どちらも
  「**ex/ルールボックスの攻撃**を無効化」する仕組み → **完全非ex の我々には全て無効**。
- 我々のプライズレース（Trevenant 140/130+100）が mill 速度（最大4枚/ターン＋セットアップ）より速い。
- 懸念だった自己ドロー（Dudunsparce 等）による自山消費は、決着が先に付くため問題にならず。

## 結論
- **LO は ex メタ捕食型**。1083.6 はラダーの ex 過半に対して稼いだもの。非ex の我々はむしろ捕食側。
- v012 の対応不要。LO 移植も不要（我々の非ex より弱い相手に勝つ道具で、ミラー飽和リスクもある）。
- メタ含意: LO が流行れば ex が減り、**非ex の我々には追い風**。/meta-watch で LO シェアを監視対象に
  （fine_classify に Great Tusk 58 のシグネチャ追加余地）。

## 資産
- `load_lo.py`（LO agent ローダ, 再利用可）/ `lo_agent/`（3rd-party, gitignored）/ `eval_lo.py`
