# exp016_pubnb — SESSION NOTES

公開ノートブック3点（2026-06-22 取得）の分析と採用。詳細な知識は
[`references/knowledge/public_notebooks_0622.md`](../../references/knowledge/public_notebooks_0622.md)。

## 対象（raw: `references/raw/public_notebooks/`, Git管理外）
1. **rule-based-not-psychic-alakazam-best-5th** — LB5位(2日目)の完全な rule-based Alakazam（main.py＋デッキ）。
2. japanese-language-ex — 公式 Mega Lucario ex サンプルの日本語訳＋**ルール解説**（public 共有=合法の根拠）。
3. ptcg-official-top-episodes-detailed-eda-ja — 公式 top episodes EDA 方法論（51M, JSON 破損, markdown のみ救出）。

## コンプラ
private sharing 禁止だが **Kaggle 公開(Code/Discussion)の利用は許可・推奨** → 公開ノートの戦略採用は合法（出典明記）。

## 採用①: Alakazam を評価プールに追加（外部コード実行はユーザー承認済み）
- `load_alakazam.py`（cg を load してから main.py を exec, deck.csv は cwd から読む）、`eval_vs_alakazam.py`。
- 3rd-party の main.py は全文レビュー済み＝純粋 rule-based（stdlib＋cg.api, deck.csv 読むだけ, ネット/subprocess/書込/eval 無し）。
- **結果（n=40, 先後入替, err 0）**:
  | 対戦 | 勝率 | 内訳 |
  |---|---|---|
  | **v008(charmq 非ex) vs Alakazam** | **0.900** | 36-4 |
  | lucario_v2(ex) vs Alakazam | 0.475 | 19-21 |
- **結論**: **v008 は Alakazam(トップ archetype)を圧倒**。懸念した Enhanced Hammer × 我々の Mist Energy は
  実戦で**無害**（剥がすには手札を消費＝Powerful Hand 打点が下がる自己矛盾。我々の機関＋Choice Band の安定打点が
  単サイド・レースに勝つ）。ex は Alakazam と五分(0.475)＝Alakazam は ex の中堅カウンター。
  → **Alakazam は我々の脅威でない**。非ex apex の優位を1つ補強。Alakazam は今後の評価プール常設候補。

## 採用②: piloting アイデア（取り込み候補, 未実装）
- **動的打点計算**: 「このターン手札を何枚増やせるか」→ 最大ダメージ事前計算で KO 判定（Alakazam の核）。
  我々の `_plan_attack` は固定ダメージ。スケーリング攻撃には動的計算が必要（我々は非スケーリングなので優先度低）。
- **山札ガード(`safe_draws`)**: 山札残≤サイド残 を避けてドロー系を制限（デッキアウト自滅回避）。我々の方策に無い安全弁。
  非ex aggro はデッキアウト稀だが、長期戦の頑健性として追加候補。

## 採用③: 公式 episodes データセット（メタ監視の拡張候補）
- `pokemon-tcg-ai-battle-episodes-index` ＋日別 `...-episodes-YYYY-MM-DD` = per-submission API より**バルクな上位リプレイ源**。
  `/meta-watch` の取得元をこれに拡張すれば、より広い上位メタを安価に追える（要 Kaggle 上での dataset 追加）。

## 不採用
- Alakazam/Lucario の公開エージェントを**そのまま提出**はしない（独創性ゼロ＝Strategy 不利）。評価相手＋アイデア源として活用。

## 出典
public_notebooks_0622.md 参照。元アイデア: heiseimikiko(why-alakazam), kiyotah(公式サンプル), ichigoe(beginner guide)。
