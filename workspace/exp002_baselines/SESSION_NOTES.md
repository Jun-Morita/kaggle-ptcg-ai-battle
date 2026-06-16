# exp002_baselines — SESSION NOTES

## 仮説
公開/公式のルールベース agent をローカルハーネスに載せ、相互の強さ関係（マッチアップ表）を
自前で測定する。あわせて公開ノートブック「Mega Lucario V2」の主張する勝率を再現検証する。

## 構成
- `extract_policies.py`: notebook(`references/raw/`)から `%%writefile main.py` を抽出し
  `policies/<name>.py` を生成、デッキを再構成して `policies/decks.json` に保存。
  （抽出物は競技/3rd-party コードのため `policies/` は gitignore。再生成はこのスクリプト。）
- `baselines.py`: policy モジュールをロードし harness 互換の agent にラップ。
  ラッパーは初手(select=None)で**デッキを注入**（モジュールの deck.csv 読みに依存しない）。
  一部 policy は import 時に deck.csv を読むため、ロード前に `policies/deck.csv` を用意。
- `run_matchups.py`: 5 ルールベース + random の総当たり（先後入替, n/pair）。勝率行列を `results/matchups.json` に保存。
- exp001 の `harness.py` を再利用。

## 対象 agent / デッキ（全60枚, 再構成検証OK）
dragapult, iono, abomasnow, lucario_v1（公式4種）, lucario_v2（公開・公式Lucarioのロジック改良版, デッキは公式と同一）, random。

## 結果 (2026-06-17, n=60/pair, swap_sides=True, seed=42)

強さ（対プール平均勝率）:
1. **lucario_v2 0.680** / 2. lucario_v1 0.647 / 3. dragapult 0.573 / 4. abomasnow 0.543 / 5. iono 0.520 / 6. random 0.037

勝率行列（行 vs 列）と特徴:
- lucario(v1/v2) がデッキとして最強。iono は abomasnow に強い(0.733)が lucario に弱い(0.25)＝じゃんけん的相性。
- 全ルールベースは random をほぼ完封(0.96–1.00)。**例外 lucario_v1 は 0.867**＝時々自滅(setup失敗)。
- **lucario_v2 vs lucario_v1 = 0.483（ほぼ五分, ノイズ内）**。V2 が総合で上な主因は**対 random 1.000 vs V1 0.867**。

### V2 公開主張の再現検証 (n=100, swap)
| マッチ | 自前再現 | 作者主張 | 判定 |
|---|---|---|---|
| v2 vs random | 0.970 | 0.99 | ほぼ一致 |
| v2 vs lucario_v1 | 0.580 | 0.707 | 乖離 |
| v2 vs dragapult | 0.550 | 0.91 | **大きく乖離** |

- 先攻有利の検証: ミラー(v2 vs v2)の先攻勝率 = 0.517 → **このエンジンの先攻有利はほぼ無い**（先攻固定説では説明不可）。
- 作者の埋め込みマッチアップ表(cell6)は**ハードコードJSON**で、公開コード(cell7, N=6 vs randomのみ)では生成されていない＝検証不能。別/古い harness か別実装の Dragapult 由来と推測。

## 考察 / 示唆
- **LB 770→796 の正体は「弱い相手への取りこぼし削減（安定性）」**。Strategy 評価でも安定性/頑健性が重視されるため、この方向は本コンペで効く。
- **公開ノートブックの勝率主張は鵜呑みにしない**。自前ハーネスがグラウンドトゥルース。CV/LB 校正は自分の数値で行う。
- ローカル強さ指標 = この固定プールに対する平均勝率。**現状の越えるべきバー = lucario_v2 0.680**。
- 相性がじゃんけん的なので、単一デッキより「対策幅」or「安定して負けにくい」設計が効く可能性。

## 次アクション
1. n を増やして(±CI)上位3者の差を確定。特に v1 vs v2 と abomasnow vs lucario。
2. exp003: Search API で1手読み（攻撃の実ダメージ/勝敗評価）を入れた自前 agent を作り、このプールで 0.680 超えを狙う。
3. lucario_v1 が random に自滅する局面をログ解析し、安定性改善の具体策を抽出。

## 出典
- 公式4種: Simulation コンペ公開 notebook（`references/raw/official_notebooks/`）。
- V2: 公開 notebook「Validated Rule-Based Agent + Matchup Tests」（`references/raw/public_notebooks/`）。
