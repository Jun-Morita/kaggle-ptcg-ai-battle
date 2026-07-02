# 公開NB「I have one REAR card」— Great Tusk LO（山札破壊）コントロール

- URL: Kaggle 公開ノートブック (PTCG AI Battle Simulation) / 取得日 2026-07-02
- スコア: **1083.6**（我々の 815 を +270 上回る、Bronze 29 votes）
- raw: `references/raw/public_notebooks/i-have-one-rear-card.ipynb`

## デッキ（60枚, deck.csv 全文あり）
- **Great Tusk 58 ×4** — 主砲。Land Collapse (attack id 62): **mill 1、Ancient サポーター使用ターンは +3=4枚**。
  「攻撃でダメージを与えない」LO 特化。Giant Tusk 160 は KO モード用。
- **Dwebble 344 ×4 / Crustle 345 ×2+2** — Safeguard 壁（ex からの攻撃無効）で時間を稼ぐ。
- Terrakion 607 ×1（バックアップ 130）。
- **Explorer's Guidance 1185 ×4**（Ancient サポーター＝mill 4 の起動鍵）、Fight Gong ×4, Poké Pad ×4,
  Poffin ×4, Pokégear ×4, Ultra Ball, Vitality Band 等。
- **Neutralization Zone 1247**（ACE SPEC stadium; 非ルールボックスは ex/V の攻撃無効）
  — 全アタッカー非exなので自軍は無傷で恩恵（exp026 で我々に不適だった札が、この構築では正解）。

## 操縦（main.py, ~55KB ルールベース）の要点
1. **モード切替**: mill（既定）/ wall（相手が ex 圧力 & 山札>20）/ KO。
2. **勝利ルートの算術比較**（should_ko_mode）: `mill_turns`（残り山札÷mill/turn＋セットアップ）と
   `ko_turns`（HP÷damage×必要KO数＋setup/switch）を**明示的に計算して速い方を選ぶ**。
   greedy スコアではなく**プラン算術**。ユーザー提供の公式ルール文書にあった
   「Relicanth/イワパレスの math-trap 戦術」の実装形。
3. 相手認識（facing_lucario / dragapult / alakazam / bench-counter 圧力）で field floor を変える。
4. 自山切れガード（own_deck_safety_guard）: 相手も LO 系のときだけ自己削り抑制。

## 我々への含意
- **脅威**: 我々の charmq/v_trev はドロー特化エンジン（Dudunsparce draw3 等で自山を高速消費）。
  LO 相手ではこの自己ドローが**そのまま敗因**になり得る。ローカル field の「crustle」= v004 壁で
  mill 要素が無いので、**この LO は未測定の別マッチアップ**。
- **機会**: (a) 操縦が完全公開（main.py+deck.csv）＝ deck⊗pilot 問題が発生しない移植候補。
  (b) 6/30 環境更新（draw→ループ側 timeout 負け）は決着型 LO に追い風。
  (c) 1083 は現メダル圏 (~1165) に近い。
- **リスク**: 公開から 2日 → 模倣者が増えメタが LO 対応に回る可能性。ミラー飽和注意。

## 実験候補
1. この agent をローカルに展開し **v012 vs LO を n=200 測定**（弱点確認が先）。3rd-party 実行は要ユーザー承認
  （import は os/collections/cg.api のみ、ネットワーク・exec なし＝安全確認済み）。
2. 勝てない場合: 対 LO ルール（例: 山札温存モード、Dudunsparce の shuffle-back 活用は実は LO 耐性がある）。
3. 移植候補としての LO デッキ自体の評価（対 ex field / 対ミラー / 対我々）。
